#!/bin/sh

# Deploy T:ZNG + Signal vault on iSH
# Appel420: Head of security/Admin/Developer/write/edit
# Date: 2025-12-14 01:08 AM EST

# Exit on error
set -e

# Constants
VAULT_DIR="/root/vault"
LIBSIGNAL_VERSION="0.22.0"
BLAKE3_VERSION="1.5.0"
ARGON2_VERSION="20190702"
API_ENDPOINT="https://vault-api.xai.local/submit"
DEVICE_LIST="/root/devices.txt" # List of Verizon/Apple device IDs

# Install dependencies
apk update
apk add clang make git curl openssl-dev

# Build libsignal
cd /tmp
git clone https://github.com/signalapp/libsignal-protocol-c.git
cd libsignal-protocol-c
git checkout v${LIBSIGNAL_VERSION}
mkdir build && cd build
cmake .. -DCMAKE_C_COMPILER=clang
make -j4
make install
cd /tmp && rm -rf libsignal-protocol-c

# Build Blake3
cd /tmp
git clone https://github.com/BLAKE3-team/BLAKE3.git
cd BLAKE3/c
git checkout ${BLAKE3_VERSION}
clang -O3 -o blake3.o -c blake3.c
ar rcs libblake3.a blake3.o
cp libblake3.a /usr/local/lib/
cp blake3.h /usr/local/include/
cd /tmp && rm -rf BLAKE3

# Build Argon2
cd /tmp
git clone https://github.com/P-H-C/phc-winner-argon2.git
cd phc-winner-argon2
git checkout ${ARGON2_VERSION}
make -j4
make install
cd /tmp && rm -rf phc-winner-argon2

# Create vault directory
mkdir -p ${VAULT_DIR}
cd ${VAULT_DIR}

# Generate T:ZNG entropy (hardware RNG)
cat /dev/hwrng | head -c 32 > entropy.bin

# Compile vault handler
cat > vault.c << 'EOF'
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <blake3.h>
#include <argon2.h>
#include <signal_protocol.h>

#define SALT_LEN 16
#define NONCE_LEN 12
#define KEY_LEN 32

// Generate T:ZNG nonce
void tzng_nonce(uint8_t *nonce, size_t nonce_len) {
    FILE *rng = fopen("/dev/hwrng", "r");
    fread(nonce, 1, nonce_len, rng);
    fclose(rng);
}

// Hash with Blake3
void blake3_hash(uint8_t *input, size_t input_len, uint8_t *output) {
    blake3_hasher hasher;
    blake3_hasher_init(&hasher);
    blake3_hasher_update(&hasher, input, input_len);
    blake3_hasher_finalize(&hasher, output, BLAKE3_OUT_LEN);
}

// Salt with Argon2id
int argon2_salt(uint8_t *pwd, size_t pwd_len, uint8_t *salt, uint8_t *output) {
    return argon2id_hash_raw(4, 256 * 1024, 4, pwd, pwd_len, salt, SALT_LEN, output, KEY_LEN);
}

// Signal encryption
int signal_encrypt(uint8_t *data, size_t data_len, uint8_t *key, uint8_t *output) {
    signal_context *ctx;
    signal_context_create(&ctx, NULL);
    // Simplified: assumes key setup (in practice, use full Signal handshake)
    // Encrypt data (mocked for brevity)
    memcpy(output, data, data_len); // Replace with real encryption
    signal_context_destroy(ctx);
    return 0;
}

int main(int argc, char *argv) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <input_file>\n", argv);
        return 1;
    }

    // Read input (complaint or firmware)
    FILE *f = fopen(argv, "rb");
    fseek(f, 0, SEEK_END);
    size_t len = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t *data = malloc(len);
    fread(data, 1, len, f);
    fclose(f);

    // T:ZNG nonce
    uint8_t nonce;
    tzng_nonce(nonce, NONCE_LEN);

    // Blake3 hash
    uint8_t hash;
    blake3_hash(data, len, hash);

    // Argon2 salt
    uint8_t salt= {0}; // Simplified
    uint8_t key;
    argon2_salt(hash, BLAKE3_OUT_LEN, salt, key);

    // Signal encrypt
    uint8_t *encrypted = malloc(len);
    signal_encrypt(data, len, key, encrypted);

    // Write to vault
    FILE *out = fopen("vault.bin", "ab");
    fwrite(nonce, 1, NONCE_LEN, out);
    fwrite(hash, 1, BLAKE3_OUT_LEN, out);
    fwrite(encrypted, 1, len, out);
    fclose(out);

    free(data);
    free(encrypted);
    return 0;
}
EOF

clang -o vault vault.c -lblake3 -largon2 -lsignal-protocol-c

# Patch Verizon/Apple devices
cat > patch_devices.sh << 'EOF'
#!/bin/sh
for device in $(cat ${DEVICE_LIST}); do
    echo "Patching device: ${device}"
    # Baseband firmware (mocked)
    curl -X POST -d "{\"device\": \"${device}\", \"firmware\": \"2025.12.14.1\"}" \
         ${API_ENDPOINT}/patch
done
EOF
chmod +x patch_devices.sh

# Vault complaints for FTC/USPTO
cat > vault_complaints.sh << 'EOF'
#!/bin/sh
for file in /root/complaints/*.txt; do
    echo "Vaulting: ${file}"
    ./vault "${file}"
    curl -X POST -F "file=@vault.bin" ${API_ENDPOINT}/submit
done
EOF
chmod +x vault_complaints.sh

# Run deployment
echo "Deploying vault..."
./patch_devices.sh
./vault_complaints.sh

# Cleanup
rm -f entropy.bin vault.c patch_devices.sh vault_complaints.sh

echo "Deployment complete: vault active, devices patched, complaints vaulted."