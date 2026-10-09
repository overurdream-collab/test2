from mcias.mfa import generate_totp, verify_totp

def test_totp_accepts_valid_code():
    secret = bytes(range(20))
    counter = 123456
    code = generate_totp(secret, counter)
    assert verify_totp(secret, code, now=counter*30) == counter

def test_totp_replay_is_rejected():
    secret = bytes(range(20))
    counter = 123456
    code = generate_totp(secret, counter)
    assert verify_totp(secret, code, last_accepted_counter=counter, now=counter*30) is None

def test_totp_invalid_input_rejected():
    secret = bytes(range(20))
    assert verify_totp(secret, "12345x", now=0) is None
    assert verify_totp(secret, "１２３４５６", now=0) is None
