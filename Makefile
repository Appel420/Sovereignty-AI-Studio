# Sovereignty-AI-Studio
# No bullshit.

CC      = clang++
SWIFT   = swiftc
RUST    = cargo
PORT    = 9898

all: swift rust cpp deploy

swift:
\t@swiftc Arc.swift Main.swift Honey.swift -O -o build/AraApp
\t@mkdir -p build && codesign -f -s "Sovereignty Root" build/AraApp

rust:
\t@cd crypto && $(RUST) build --release
\t@cp crypto/target/release/libvault.so .

cpp:
\t@$(CC) -fPIC -shared -O2 main_v1_7_sovereign.cpp -o libsovereign.dylib

deploy:
\t@ldconfig -n . 2>/dev/null || true
\t@python3 -m http.server $(PORT) --bind 127.0.0.1 &
\t@cp ara_listener /root/bin/ara
\t@chmod +x /root/bin/ara
\t@/root/bin/ara --voice=on

clean:
\t@rm -rf build *.dylib *.so *.ipa *.app
\t@cargo clean

.PHONY: all swift rust cpp deploy clean