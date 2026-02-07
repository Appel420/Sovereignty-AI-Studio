# Sovereignty AI Studio - Multi-Language Build System
# Compiles C++, Swift, Rust components and deploys the full stack

# Configuration
CC = clang++
SWIFTC = swiftc
CARGO = cargo
INSTALL_DIR = /root/bin
SERVER_PORT = 9898
SERVER_HOST = 127.0.0.1

# Output targets
LIBSOVEREIGN = build/libsovereign.dylib
ARA_APP = build/AraApp.ipa
VAULT_SO = crypto/vault.so

# Source files
CPP_SRC = main_v1_7_sovereign.cpp
SWIFT_SRC = Arc.swift Main.swift Honey.swift
RUST_SRC = build.rs Alerts.Rust Fortress-Protocol-7.887.Rust

# Build flags
CPPFLAGS = -std=c++17 -O2 -fPIC -shared
SWIFTFLAGS = -O -whole-module-optimization
RUSTFLAGS = --release

.PHONY: all build compile deploy install activate clean help

all: build deploy install activate

help:
	@echo "Sovereignty AI Studio Build System"
	@echo "=================================="
	@echo "make build     - Compile all components (C++, Swift, Rust)"
	@echo "make compile   - Same as build"
	@echo "make deploy    - Sign, push, and load to server"
	@echo "make install   - Install Ara listener to $(INSTALL_DIR)"
	@echo "make activate  - Activate 'Hey Ara' voice command"
	@echo "make clean     - Remove build artifacts"
	@echo "make all       - Complete build, deploy, and activation"

# Create build directories
build-dirs:
	@mkdir -p build
	@mkdir -p crypto
	@mkdir -p $(INSTALL_DIR)

# Build C++ library
$(LIBSOVEREIGN): $(CPP_SRC) build-dirs
	@echo "🔨 Building C++ library: libsovereign.dylib"
	$(CC) $(CPPFLAGS) -o $(LIBSOVEREIGN) $(CPP_SRC)
	@echo "✅ C++ library built successfully"

# Build Swift iOS app
$(ARA_APP): $(SWIFT_SRC) build-dirs
	@echo "🔨 Building Swift iOS app: AraApp.ipa"
	@xcodebuild -project AraApp.xcodeproj -scheme AraApp -configuration Release archive \
		-archivePath build/AraApp.xcarchive
	@xcodebuild -exportArchive -archivePath build/AraApp.xcarchive \
		-exportPath build -exportOptionsPlist exportOptions.plist
	@echo "✅ Swift app built successfully"

# Build Rust crypto module
$(VAULT_SO): $(RUST_SRC) build-dirs
	@echo "🔨 Building Rust crypto module: vault.so"
	@$(CARGO) build $(RUSTFLAGS) --lib
	@cp target/release/libvault.so $(VAULT_SO)
	@echo "✅ Rust module built successfully"

# Main build target
build: $(LIBSOVEREIGN) $(ARA_APP) $(VAULT_SO)
	@echo "🎉 All components built successfully!"

compile: build

# Code signing
sign: build
	@echo "🔐 Signing binaries..."
	@codesign --force --sign "Sovereignty Developer" $(LIBSOVEREIGN)
	@codesign --force --sign "Sovereignty Developer" $(ARA_APP)
	@echo "✅ Binaries signed"

# Deploy to server
deploy: sign
	@echo "🚀 Deploying to $(SERVER_HOST):$(SERVER_PORT)..."
	@./scripts/deploy.sh $(LIBSOVEREIGN) $(ARA_APP) $(VAULT_SO)
	@echo "📡 Starting server on $(SERVER_HOST):$(SERVER_PORT)..."
	@python3 -m http.server $(SERVER_PORT) --bind $(SERVER_HOST) &
	@echo "✅ Deployment complete - Server live at http://$(SERVER_HOST):$(SERVER_PORT)"

# Install Ara listener
install: build
	@echo "📦 Installing Ara listener to $(INSTALL_DIR)..."
	@cp build/ara_listener $(INSTALL_DIR)/ara
	@chmod +x $(INSTALL_DIR)/ara
	@echo "✅ Ara listener installed"

# Activate voice command
activate: install
	@echo "🎤 Activating 'Hey Ara' voice command..."
	@$(INSTALL_DIR)/ara --enable-voice-activation
	@echo "��� Hey Ara is now active!"
	@echo "   Say 'Hey Ara' to activate the assistant"

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	@rm -rf build/
	@rm -f $(VAULT_SO)
	@$(CARGO) clean
	@echo "✅ Clean complete"

# Development watch mode
watch:
	@echo "👁️  Watching for file changes..."
	@fswatch -o $(CPP_SRC) $(SWIFT_SRC) $(RUST_SRC) | xargs -n1 -I{} make build

# Run tests
test: build
	@echo "🧪 Running tests..."
	@python3 -m pytest tests/
	@$(CARGO) test
	@echo "✅ All tests passed"

# Quick rebuild
rebuild: clean build

# Status check
status:
	@echo "📊 Build Status:"
	@echo "  C++ Library:  $(shell [ -f $(LIBSOVEREIGN) ] && echo '✅' || echo '❌')"
	@echo "  Swift App:    $(shell [ -f $(ARA_APP) ] && echo '✅' || echo '❌')"
	@echo "  Rust Module:  $(shell [ -f $(VAULT_SO) ] && echo '✅' || echo '❌')"
	@echo "  Server:       $(shell curl -s http://$(SERVER_HOST):$(SERVER_PORT) > /dev/null && echo '✅ Live' || echo '❌ Offline')"
	@echo "  Ara Listener: $(shell [ -f $(INSTALL_DIR)/ara ] && echo '✅ Installed' || echo '❌ Not installed')"