from finreq.masking import mask_text


def test_masks_email_without_swallowing_trailing_punctuation():
    result = mask_text("Contact ravi.k@example.com. Thanks.")
    assert "ravi.k@example.com" not in result.masked_text
    assert result.masked_text == "Contact [EMAIL_1]. Thanks."


def test_same_value_reuses_same_placeholder():
    result = mask_text("Card 4111111111111111 and again 4111111111111111.")
    assert result.masked_text.count("[CARD_1]") == 2
    assert len(result.mapping) == 1


def test_masks_pan_ifsc_phone_and_account():
    text = "PAN ABCDE1234F, IFSC HDFC0001234, call +91 9876543210, a/c 123456789012."
    result = mask_text(text)
    for token in ("ABCDE1234F", "HDFC0001234", "9876543210", "123456789012"):
        assert token not in result.masked_text
    assert "[PAN_1]" in result.masked_text
    assert "[IFSC_1]" in result.masked_text
    assert "[PHONE_1]" in result.masked_text
    assert "[ACCOUNT_1]" in result.masked_text


def test_unmask_restores_original_values():
    original = "Email ravi.k@example.com and account 123456789012."
    result = mask_text(original)
    assert result.unmask(result.masked_text) == original


def test_distinct_values_get_distinct_placeholders():
    result = mask_text("a@b.com and c@d.com")
    assert result.masked_text == "[EMAIL_1] and [EMAIL_2]"
