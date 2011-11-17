DIST=dist
PACKAGE=export_freemind
SRCFILES=info.xml __init__.py
CONTENTS=$(addprefix $(PACKAGE)/,$(SRCFILES))
DESTINATION=$(HOME)/.config/keepnote/extensions/$(PACKAGE)

ZIP=/usr/bin/env zip

install: $(CONTENTS)
	mkdir -p $(DESTINATION)
	cp $(CONTENTS) $(DESTINATION)/	

$(DIST)/$(PACKAGE).kne: $(CONTENTS) dist
	$(ZIP) $@ $(CONTENTS)

$(DIST):
	mkdir -p $(DIST)

clean:
	rm -fr $(DIST)
