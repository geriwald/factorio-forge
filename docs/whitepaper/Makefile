# =====================================================================
#  Makefile for the Factorio Forge whitepaper.
#
#  Builds whitepaper.pdf into the project-level build/ directory
#  (../../build, gitignored). latexmk is preferred; if it is not
#  installed, a manual pdflatex + bibtex fallback is used.
# =====================================================================

MAIN       := whitepaper
BIB        := references
BUILDDIR   := ../../build
PDF        := $(BUILDDIR)/$(MAIN).pdf

# Detect latexmk; fall back to manual passes when absent.
LATEXMK    := $(shell command -v latexmk 2>/dev/null)

PDFLATEX      := pdflatex
PDFLATEXOPTS  := -interaction=nonstopmode -halt-on-error -file-line-error \
                 -output-directory=$(BUILDDIR)

.PHONY: all clean distclean watch wordcount help

all: $(PDF)

$(BUILDDIR):
	mkdir -p $(BUILDDIR)

$(PDF): $(MAIN).tex $(BIB).bib | $(BUILDDIR)
ifneq ($(LATEXMK),)
	$(LATEXMK) -pdf -bibtex -interaction=nonstopmode -halt-on-error \
	           -output-directory=$(BUILDDIR) $(MAIN).tex
else
	# Manual pdflatex + bibtex cycle (no latexmk available).
	# bibtex refuses '..' output paths under openout_any=p, so run it
	# with CWD inside the build dir and point BIBINPUTS back at the source.
	$(PDFLATEX) $(PDFLATEXOPTS) $(MAIN).tex
	cd $(BUILDDIR) && BIBINPUTS="$(CURDIR):" bibtex $(MAIN)
	$(PDFLATEX) $(PDFLATEXOPTS) $(MAIN).tex
	$(PDFLATEX) $(PDFLATEXOPTS) $(MAIN).tex
endif

watch:
ifneq ($(LATEXMK),)
	$(LATEXMK) -pdf -bibtex -pvc -interaction=nonstopmode \
	           -output-directory=$(BUILDDIR) $(MAIN).tex
else
	@echo "latexmk not installed: 'make watch' is unavailable. Run 'make' on change."
endif

wordcount:
	@command -v texcount >/dev/null 2>&1 \
	  && texcount -inc -total $(MAIN).tex \
	  || echo "texcount not installed."

clean:
	rm -f $(BUILDDIR)/$(MAIN).aux $(BUILDDIR)/$(MAIN).bbl $(BUILDDIR)/$(MAIN).blg \
	      $(BUILDDIR)/$(MAIN).log $(BUILDDIR)/$(MAIN).out $(BUILDDIR)/$(MAIN).toc \
	      $(BUILDDIR)/$(MAIN).lof $(BUILDDIR)/$(MAIN).lot $(BUILDDIR)/$(MAIN).fls \
	      $(BUILDDIR)/$(MAIN).fdb_latexmk

distclean: clean
	rm -f $(PDF)

help:
	@echo "Targets:"
	@echo "  make            build $(PDF)"
	@echo "  make watch      continuous rebuild (requires latexmk)"
	@echo "  make wordcount  texcount word count"
	@echo "  make clean      remove auxiliary files"
	@echo "  make distclean  remove auxiliary files and the PDF"
