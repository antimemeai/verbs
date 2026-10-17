PREFIX ?= /usr/local
LIBDIR ?= $(PREFIX)/lib

all: build/verbs.cma

build/verbs.cma: verbs.mli verbs.ml
	mkdir -p build
	ocamlc -c -o build/verbs.cmi verbs.mli
	ocamlc -I build -c -o build/verbs.cmo verbs.ml
	ocamlc -a -o build/verbs.cma build/verbs.cmo

test: all
	ocamlc -I build -c -o build/test.cmo test.ml
	ocamlc -I build -o build/test build/verbs.cma build/test.cmo
	./build/test

install: all
	mkdir -p $(DESTDIR)$(LIBDIR)/verbs
	cp build/verbs.cmi build/verbs.cma verbs.mli META $(DESTDIR)$(LIBDIR)/verbs/

clean:
	rm -rf build

.PHONY: all test install clean
