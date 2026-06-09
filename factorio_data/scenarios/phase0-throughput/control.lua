-- Phase 0 throughput scenario: player-less headless materialization.
--
-- On init: decode an embedded blueprint string, create_entity every entity on
-- nauvis (bypassing ghosts), wire up infinite power and an infinite input feed,
-- warm up, then measure the rate at which the target item is CONVEYED into the
-- output (sink) chest over a fixed window. The result is written to
-- script-output/phase0-result.json.
--
-- We measure conveyed throughput (delta of the item count in the sink chest),
-- not raw machine production: a design's efficiency is what actually reaches the
-- output, not what the machines theoretically craft. Raw machine production
-- (products_finished) is collected as a secondary figure so the conveyance yield
-- (conveyed / produced) can be derived later -- a saturated belt/full sink is
-- both higher-throughput and cheaper for the engine to simulate (UPS).
--
-- Parameters (blueprint, target item, tick windows) live in params.lua, which
-- the Python harness generates per run. This file is the fixed engine.

local params = require("params")

local WARMUP_TICKS = params.warmup_ticks
local MEASURE_TICKS = params.measure_ticks
local T_MEASURE_START = WARMUP_TICKS
local T_MEASURE_END = WARMUP_TICKS + MEASURE_TICKS

local function decode_blueprint_entities(blueprint_string)
  -- A script inventory gives us a LuaItemStack without needing a player.
  local inv = game.create_inventory(1)
  local stack = inv[1]
  stack.set_stack({ name = "blueprint" })
  local code = stack.import_stack(blueprint_string)
  if code == 1 then
    error("import_stack failed (code 1) on the blueprint string")
  end
  local entities = stack.get_blueprint_entities()
  inv.destroy()
  return entities or {}
end

local function materialize(surface, force, entities)
  local created = {}
  local crafters = {}
  for _, e in pairs(entities) do
    local entity = surface.create_entity({
      name = e.name,
      position = e.position,
      direction = e.direction,
      force = force,
      raise_built = false,
    })
    if entity then
      -- Assembling machines carry an explicit recipe; furnaces auto-select
      -- theirs from the inserted input, so they must not be set.
      if e.recipe and entity.type == "assembling-machine" then
        entity.set_recipe(e.recipe)
      end
      if entity.type == "furnace" or entity.type == "assembling-machine" then
        crafters[#crafters + 1] = entity
      end
      created[#created + 1] = entity
    end
  end
  storage.crafters = crafters
  return created
end

local function configure_feed(created)
  -- First infinity-chest = source (infinite input feed); last = sink (passive
  -- output container we measure). electric-energy-interface supplies power.
  local chests = {}
  for _, ent in pairs(created) do
    if ent.name == "infinity-chest" then
      chests[#chests + 1] = ent
    elseif ent.name == "electric-energy-interface" then
      -- Runtime API wants numeric joules/watts, not UI strings like "500GW".
      ent.power_production = 5e11  -- 500 GW
      ent.electric_buffer_size = 5e11
      ent.energy = 5e11
    end
  end
  -- Source chest: infinitely supply the input item.
  if chests[1] then
    chests[1].infinity_container_filters = {
      {
        index = 1,
        name = params.input_item,
        count = chests[1].prototype.get_inventory_size(defines.inventory.chest),
        mode = "exactly",
      },
    }
    chests[1].remove_unfiltered_items = false
  end
  -- Sink chest: left passive (no infinity void) so conveyed items accumulate and
  -- can be counted. It is the LAST infinity-chest in the blueprint.
  storage.sink = chests[#chests]
end

local function sink_count()
  if not (storage.sink and storage.sink.valid) then return 0 end
  return storage.sink.get_item_count(params.target_item)
end

local function products_finished_total()
  local total = 0
  for _, c in pairs(storage.crafters or {}) do
    if c.valid then total = total + c.products_finished end
  end
  return total
end

local function setup()
  local surface = game.surfaces[1]
  local force = game.forces.player
  storage.surface = surface
  storage.force = force

  local entities = decode_blueprint_entities(params.blueprint)
  local created = materialize(surface, force, entities)
  configure_feed(created)
  storage.created_count = #created

  -- A headless server pauses ticks while no player is connected; unpause so the
  -- factory runs and on_nth_tick fires.
  game.tick_paused = false

  -- Run faster than real time (CPU-bound). The per-tick throughput is unchanged,
  -- so the measurement stays valid; we just simulate the window in less wall time.
  game.speed = params.game_speed
end

script.on_init(setup)

script.on_nth_tick(1, function(event)
  local tick = event.tick
  if tick == T_MEASURE_START then
    storage.sink_start = sink_count()
    storage.produced_start = products_finished_total()
  elseif tick == T_MEASURE_END then
    local conveyed = sink_count() - (storage.sink_start or 0)
    local produced = products_finished_total() - (storage.produced_start or 0)
    local seconds = MEASURE_TICKS / 60.0
    helpers.write_file(
      "phase0-result.json",
      helpers.table_to_json({
        target_item = params.target_item,
        measure_ticks = MEASURE_TICKS,
        -- Primary: conveyed throughput (what reached the sink chest).
        conveyed = conveyed,
        rate_per_second = conveyed / seconds,
        -- Secondary: raw machine production, for conveyance-yield analysis.
        produced = produced,
        produced_per_second = produced / seconds,
        materialized_entities = storage.created_count,
      }),
      false
    )
    -- Signal completion; the harness polls for the result file and terminates
    -- the process. In debug (windowed) mode we keep the game open to watch.
    if not params.keep_open then
      game.set_game_state({ game_finished = true, player_won = true, can_continue = false })
    end
  end
end)
