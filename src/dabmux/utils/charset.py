"""
Character set handling for DAB.

This module implements conversion between UTF-8 and EBU Latin charset
as specified in ETSI EN 300 401.
"""
from typing import Optional

# EBU Latin character set mapping (0x00-0x7F is ASCII, 0x80-0xFF is extended)
# Based on ETSI EN 300 401 Table 2
EBU_LATIN_TO_UNICODE = {
    # 0x00-0x7F: Standard ASCII (identity mapping)
    **{i: chr(i) for i in range(0x80)},

    # 0x80-0xFF: EBU Latin extended characters
    0x80: '\u0000',  # Unused
    0x81: '\u0104',  # Ą - Latin capital letter A with ogonek
    0x82: '\u0112',  # Ē - Latin capital letter E with macron
    0x83: '\u0122',  # Ģ - Latin capital letter G with cedilla
    0x84: '\u012A',  # Ī - Latin capital letter I with macron
    0x85: '\u0136',  # Ķ - Latin capital letter K with cedilla
    0x86: '\u013B',  # Ļ - Latin capital letter L with cedilla
    0x87: '\u0145',  # Ņ - Latin capital letter N with cedilla
    0x88: '\u014C',  # Ō - Latin capital letter O with macron
    0x89: '\u0156',  # Ŗ - Latin capital letter R with cedilla
    0x8A: '\u015A',  # Ś - Latin capital letter S with acute
    0x8B: '\u0166',  # Ŧ - Latin capital letter T with stroke
    0x8C: '\u016A',  # Ū - Latin capital letter U with macron
    0x8D: '\u0179',  # Ź - Latin capital letter Z with acute
    0x8E: '\u017B',  # Ż - Latin capital letter Z with dot above
    0x8F: '\u017D',  # Ž - Latin capital letter Z with caron

    0x90: '\u0105',  # ą - Latin small letter a with ogonek
    0x91: '\u0113',  # ē - Latin small letter e with macron
    0x92: '\u0123',  # ģ - Latin small letter g with cedilla
    0x93: '\u012B',  # ī - Latin small letter i with macron
    0x94: '\u0137',  # ķ - Latin small letter k with cedilla
    0x95: '\u013C',  # ļ - Latin small letter l with cedilla
    0x96: '\u0146',  # ņ - Latin small letter n with cedilla
    0x97: '\u014D',  # ō - Latin small letter o with macron
    0x98: '\u0157',  # ŗ - Latin small letter r with cedilla
    0x99: '\u015B',  # ś - Latin small letter s with acute
    0x9A: '\u0167',  # ŧ - Latin small letter t with stroke
    0x9B: '\u016B',  # ū - Latin small letter u with macron
    0x9C: '\u017A',  # ź - Latin small letter z with acute
    0x9D: '\u017C',  # ż - Latin small letter z with dot above
    0x9E: '\u017E',  # ž - Latin small letter z with caron
    0x9F: '\u0000',  # Unused

    0xA0: '\u00A0',  # Non-breaking space
    0xA1: '\u00A1',  # ¡ - Inverted exclamation mark
    0xA2: '\u00A2',  # ¢ - Cent sign
    0xA3: '\u00A3',  # £ - Pound sign
    0xA4: '\u0024',  # $ - Dollar sign
    0xA5: '\u00A5',  # ¥ - Yen sign
    0xA6: '\u0023',  # # - Number sign
    0xA7: '\u00A7',  # § - Section sign
    0xA8: '\u00A4',  # ¤ - Currency sign
    0xA9: '\u2018',  # ' - Left single quotation mark
    0xAA: '\u201C',  # " - Left double quotation mark
    0xAB: '\u00AB',  # « - Left-pointing double angle quotation mark
    0xAC: '\u2190',  # ← - Leftwards arrow
    0xAD: '\u2191',  # ↑ - Upwards arrow
    0xAE: '\u2192',  # → - Rightwards arrow
    0xAF: '\u2193',  # ↓ - Downwards arrow

    0xB0: '\u00B0',  # ° - Degree sign
    0xB1: '\u00B1',  # ± - Plus-minus sign
    0xB2: '\u00B2',  # ² - Superscript two
    0xB3: '\u00B3',  # ³ - Superscript three
    0xB4: '\u00D7',  # × - Multiplication sign
    0xB5: '\u00B5',  # µ - Micro sign
    0xB6: '\u00B6',  # ¶ - Pilcrow sign
    0xB7: '\u00B7',  # · - Middle dot
    0xB8: '\u00F7',  # ÷ - Division sign
    0xB9: '\u2019',  # ' - Right single quotation mark
    0xBA: '\u201D',  # " - Right double quotation mark
    0xBB: '\u00BB',  # » - Right-pointing double angle quotation mark
    0xBC: '\u00BC',  # ¼ - Vulgar fraction one quarter
    0xBD: '\u00BD',  # ½ - Vulgar fraction one half
    0xBE: '\u00BE',  # ¾ - Vulgar fraction three quarters
    0xBF: '\u00BF',  # ¿ - Inverted question mark

    0xC0: '\u00C0',  # À - Latin capital letter A with grave
    0xC1: '\u00C1',  # Á - Latin capital letter A with acute
    0xC2: '\u00C2',  # Â - Latin capital letter A with circumflex
    0xC3: '\u00C3',  # Ã - Latin capital letter A with tilde
    0xC4: '\u00C4',  # Ä - Latin capital letter A with diaeresis
    0xC5: '\u00C5',  # Å - Latin capital letter A with ring above
    0xC6: '\u00C6',  # Æ - Latin capital letter AE
    0xC7: '\u00C7',  # Ç - Latin capital letter C with cedilla
    0xC8: '\u00C8',  # È - Latin capital letter E with grave
    0xC9: '\u00C9',  # É - Latin capital letter E with acute
    0xCA: '\u00CA',  # Ê - Latin capital letter E with circumflex
    0xCB: '\u00CB',  # Ë - Latin capital letter E with diaeresis
    0xCC: '\u00CC',  # Ì - Latin capital letter I with grave
    0xCD: '\u00CD',  # Í - Latin capital letter I with acute
    0xCE: '\u00CE',  # Î - Latin capital letter I with circumflex
    0xCF: '\u00CF',  # Ï - Latin capital letter I with diaeresis

    0xD0: '\u00D0',  # Ð - Latin capital letter Eth
    0xD1: '\u00D1',  # Ñ - Latin capital letter N with tilde
    0xD2: '\u00D2',  # Ò - Latin capital letter O with grave
    0xD3: '\u00D3',  # Ó - Latin capital letter O with acute
    0xD4: '\u00D4',  # Ô - Latin capital letter O with circumflex
    0xD5: '\u00D5',  # Õ - Latin capital letter O with tilde
    0xD6: '\u00D6',  # Ö - Latin capital letter O with diaeresis
    0xD7: '\u0152',  # Œ - Latin capital ligature OE
    0xD8: '\u00D8',  # Ø - Latin capital letter O with stroke
    0xD9: '\u00D9',  # Ù - Latin capital letter U with grave
    0xDA: '\u00DA',  # Ú - Latin capital letter U with acute
    0xDB: '\u00DB',  # Û - Latin capital letter U with circumflex
    0xDC: '\u00DC',  # Ü - Latin capital letter U with diaeresis
    0xDD: '\u00DD',  # Ý - Latin capital letter Y with acute
    0xDE: '\u00DE',  # Þ - Latin capital letter Thorn
    0xDF: '\u00DF',  # ß - Latin small letter sharp s

    0xE0: '\u00E0',  # à - Latin small letter a with grave
    0xE1: '\u00E1',  # á - Latin small letter a with acute
    0xE2: '\u00E2',  # â - Latin small letter a with circumflex
    0xE3: '\u00E3',  # ã - Latin small letter a with tilde
    0xE4: '\u00E4',  # ä - Latin small letter a with diaeresis
    0xE5: '\u00E5',  # å - Latin small letter a with ring above
    0xE6: '\u00E6',  # æ - Latin small letter ae
    0xE7: '\u00E7',  # ç - Latin small letter c with cedilla
    0xE8: '\u00E8',  # è - Latin small letter e with grave
    0xE9: '\u00E9',  # é - Latin small letter e with acute
    0xEA: '\u00EA',  # ê - Latin small letter e with circumflex
    0xEB: '\u00EB',  # ë - Latin small letter e with diaeresis
    0xEC: '\u00EC',  # ì - Latin small letter i with grave
    0xED: '\u00ED',  # í - Latin small letter i with acute
    0xEE: '\u00EE',  # î - Latin small letter i with circumflex
    0xEF: '\u00EF',  # ï - Latin small letter i with diaeresis

    0xF0: '\u00F0',  # ð - Latin small letter eth
    0xF1: '\u00F1',  # ñ - Latin small letter n with tilde
    0xF2: '\u00F2',  # ò - Latin small letter o with grave
    0xF3: '\u00F3',  # ó - Latin small letter o with acute
    0xF4: '\u00F4',  # ô - Latin small letter o with circumflex
    0xF5: '\u00F5',  # õ - Latin small letter o with tilde
    0xF6: '\u00F6',  # ö - Latin small letter o with diaeresis
    0xF7: '\u0153',  # œ - Latin small ligature oe
    0xF8: '\u00F8',  # ø - Latin small letter o with stroke
    0xF9: '\u00F9',  # ù - Latin small letter u with grave
    0xFA: '\u00FA',  # ú - Latin small letter u with acute
    0xFB: '\u00FB',  # û - Latin small letter u with circumflex
    0xFC: '\u00FC',  # ü - Latin small letter u with diaeresis
    0xFD: '\u00FD',  # ý - Latin small letter y with acute
    0xFE: '\u00FE',  # þ - Latin small letter thorn
    0xFF: '\u00FF',  # ÿ - Latin small letter y with diaeresis
}

# Reverse mapping: Unicode to EBU Latin
UNICODE_TO_EBU_LATIN = {v: k for k, v in EBU_LATIN_TO_UNICODE.items() if v != '\u0000'}


def utf8_to_ebu_latin(text: str, max_length: int = 16, pad: bool = True) -> bytes:
    """
    Convert UTF-8 string to EBU Latin charset.

    Args:
        text: UTF-8 input string
        max_length: Maximum output length in bytes
        pad: Pad with spaces to max_length

    Returns:
        EBU Latin encoded bytes

    Raises:
        ValueError: If character cannot be encoded in EBU Latin
    """
    result = bytearray()

    for char in text:
        if len(result) >= max_length:
            break

        # Try direct ASCII mapping (0x00-0x7F)
        if ord(char) < 0x80:
            result.append(ord(char))
        # Try EBU Latin extended mapping
        elif char in UNICODE_TO_EBU_LATIN:
            result.append(UNICODE_TO_EBU_LATIN[char])
        # Character not supported
        else:
            # Replace with space or question mark
            result.append(0x20)  # Space

    # Pad with spaces if requested
    if pad and len(result) < max_length:
        result.extend(b' ' * (max_length - len(result)))

    return bytes(result[:max_length])


def ebu_latin_to_utf8(data: bytes) -> str:
    """
    Convert EBU Latin charset to UTF-8 string.

    Args:
        data: EBU Latin encoded bytes

    Returns:
        UTF-8 string
    """
    result = []

    for byte in data:
        if byte in EBU_LATIN_TO_UNICODE:
            char = EBU_LATIN_TO_UNICODE[byte]
            if char != '\u0000':  # Skip unused characters
                result.append(char)
        else:
            result.append(' ')  # Fallback for unknown bytes

    # Strip trailing spaces
    return ''.join(result).rstrip()


def calculate_label_short_mask(label: str, short_label: str) -> int:
    """
    Calculate the short label character mask.

    The mask is a 16-bit value where each bit indicates whether the
    corresponding character in the full label is part of the short label.

    Args:
        label: Full label (up to 16 characters)
        short_label: Short label (up to 8 characters)

    Returns:
        16-bit character mask

    Raises:
        ValueError: If short label characters are not found in label
    """
    if not short_label:
        return 0

    mask = 0
    short_idx = 0

    for label_idx, char in enumerate(label):
        if label_idx >= 16:
            break

        if short_idx < len(short_label) and char == short_label[short_idx]:
            mask |= (1 << (15 - label_idx))
            short_idx += 1

    # Verify all short label characters were found
    if short_idx != len(short_label):
        raise ValueError(
            f"Short label '{short_label}' characters not found in order in label '{label}'"
        )

    return mask


def validate_label(label: str, short_label: str = "") -> bool:
    """
    Validate DAB label and short label.

    Args:
        label: Full label (max 16 characters)
        short_label: Short label (max 8 characters)

    Returns:
        True if valid

    Raises:
        ValueError: If validation fails
    """
    if len(label) > 16:
        raise ValueError(f"Label too long: {len(label)} > 16 characters")

    if len(short_label) > 8:
        raise ValueError(f"Short label too long: {len(short_label)} > 8 characters")

    # Check that all characters can be encoded in EBU Latin
    try:
        utf8_to_ebu_latin(label, max_length=16, pad=False)
        if short_label:
            utf8_to_ebu_latin(short_label, max_length=8, pad=False)
    except ValueError as e:
        raise ValueError(f"Label contains unsupported characters: {e}")

    # Check short label character mask
    if short_label:
        try:
            calculate_label_short_mask(label, short_label)
        except ValueError as e:
            raise ValueError(f"Invalid short label: {e}")

    return True
