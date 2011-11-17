DIST=dist
PACKAGE=export_freemind
SRCFILES=info.xml __init__.py
CONTENTS=$(addprefix $(PACKAGE)/,$(SRCFILES))

ZIP=/usr/bin/env zip

$(DIST)/$(PACKAGE).kne: $(CONTENTS) dist
	$(ZIP) $@ $(CONTENTS)

$(DIST):
	mkdir -p $(DIST)

clean:
	rm -fr $(DIST)
