use pqcrypto_falcon::falcon1024 as falcon;
use pqcrypto_traits::sign::{PublicKey, SecretKey, DetachedSignature};

#[no_mangle]
pub extern "C" fn falcon_sign(
    message_ptr: *const u8,
    message_len: usize,
    sk_ptr: *const u8,
    sk_len: usize,
    sig_out: *mut u8,
    sig_len: *mut usize,
) -> i32 {
    unsafe {
        if message_ptr.is_null() || sk_ptr.is_null() || sig_out.is_null() || sig_len.is_null() { return -1; }
        let message = std::slice::from_raw_parts(message_ptr, message_len);
        let sk_bytes = std::slice::from_raw_parts(sk_ptr, sk_len);
        let secret_key = match falcon::SecretKey::from_bytes(sk_bytes) { Ok(k) => k, Err(_) => return -2 };
        let signature = falcon::detached_sign(message, &secret_key);
        let sig_bytes = signature.as_bytes();
        if sig_bytes.len() > *sig_len { return -3; }
        std::ptr::copy_nonoverlapping(sig_bytes.as_ptr(), sig_out, sig_bytes.len());
        *sig_len = sig_bytes.len();
        0
    }
}

#[no_mangle]
pub extern "C" fn falcon_verify(
    message_ptr: *const u8,
    message_len: usize,
    sig_ptr: *const u8,
    sig_len: usize,
    pk_ptr: *const u8,
    pk_len: usize,
) -> i32 {
    unsafe {
        if message_ptr.is_null() || sig_ptr.is_null() || pk_ptr.is_null() { return -1; }
        let message = std::slice::from_raw_parts(message_ptr, message_len);
        let sig_bytes = std::slice::from_raw_parts(sig_ptr, sig_len);
        let pk_bytes = std::slice::from_raw_parts(pk_ptr, pk_len);
        let public_key = match falcon::PublicKey::from_bytes(pk_bytes) { Ok(k) => k, Err(_) => return -2 };
        let signature = match falcon::DetachedSignature::from_bytes(sig_bytes) { Ok(s) => s, Err(_) => return -3 };
        match falcon::verify_detached_signature(&signature, message, &public_key) { Ok(_) => 0, Err(_) => -4 }
    }
}
