"""Pure keyed uniform values for the common seed/RNG foundation.

This module does not choose routes, assign arrival tiebreakers, or run
merge selection. It only stores a normalized entropy representation and
turns an explicit key into one uniform value in ``[0, 1)``.

The value is a shared random input for a named research event. The same
entropy, domain, and key always return the same value. A different route
preference or candidate set may still select a different link later.
Callers must not read ``World.random_seed`` again inside this module.
"""

import hashlib
import numbers


SERIALIZATION_VERSION = 1
_FORMAT_PREFIX_BASE = b"UXSIM_COMMON_SEED_RNG_V"
_VERSION_ASCII = str(SERIALIZATION_VERSION).encode("ascii")
FORMAT_PREFIX = _FORMAT_PREFIX_BASE + _VERSION_ASCII

# SHA-256 is in the Python standard library, has a fixed 32-byte digest,
# and does not depend on process-wide hash randomization.
HASH_ALGORITHM_NAME = "sha256"
DIGEST_SIZE_BYTES = 32

# A Python float has a 53-bit integer mantissa. Using more than 53 bits can
# round to 1.0. Dividing an integer in ``0 .. 2**53-1`` by ``2**53`` stays
# strictly below 1.0 and uses every exact integer a float can represent.
UNIFORM_BIT_COUNT = 53
UNIFORM_BYTE_COUNT = 8
UNIFORM_SHIFT = (UNIFORM_BYTE_COUNT * 8) - UNIFORM_BIT_COUNT

FIELD_ENTROPY = b"E"
FIELD_DOMAIN = b"D"
TYPE_STRING = b"S"
TYPE_NONNEGATIVE_INT = b"I"
SIGN_NONNEGATIVE = b"\x00"


def normalize_seed_sequence_entropy(raw_entropy):
    """Copy SeedSequence entropy into a tuple of non-negative Python ints.

    ``World.__init__`` already built the ``SeedSequence`` used for
    ``order_control_rng``. This function only reads that object's
    ``entropy`` attribute. It does not call ``SeedSequence(None)`` again,
    does not spawn another child sequence, and does not draw from any
    Generator. No additional OS entropy, spawn, or Generator consumption
    happens here.

    On NumPy 2.3.5 (confirmed in Terminal), ``SeedSequence.entropy`` is a
    single Python ``int`` for an explicit integer seed (for example
    ``SeedSequence(0).entropy`` is ``0`` and ``SeedSequence(7).entropy`` is
    ``7``) and for ``SeedSequence(None)`` (one large integer holding the OS
    entropy that was drawn once when that ``SeedSequence`` was created).
    For that shape, this function wraps the single integer as a one-element
    tuple.

    The internal stored form is always a non-empty ``tuple`` of non-negative
    Python ``int`` values, not a bare integer. Keyed serialization then
    uses one explicit layout for entropy whether the input was one integer
    or several. Iterable input remains supported: if a future or alternate
    NumPy version, or another acceptable caller, passes a sequence of
    integers, each element is converted to a Python ``int`` in order. This
    function does not split one integer into multiple words on its own.

    Plain Python ``int`` elements are stored so the result pickles without
    retaining NumPy scalar types.

    Accepted inputs:

    - One non-negative Python ``int`` (including a large ``SeedSequence``
      entropy integer).
    - One non-negative NumPy integer scalar, stored as a one-element tuple of
      Python ``int``.
    - A non-empty iterable of non-negative integers (for example a tuple,
      list, or a NumPy array of integer words).

    Rejected inputs (``ValueError``):

    - ``bool``.
    - Negative integers.
    - ``str``, ``bytes``, ``bytearray``, and ``dict`` (they must not be
      mistaken for integer word sequences).
    - Empty iterables.
    - Non-integer elements inside an iterable.
    - Values that cannot be iterated as an integer sequence.

    Parameters
    ----------
    raw_entropy
        ``SeedSequence.entropy`` from the existing order-control seed
        sequence, or another acceptable value listed above.

    Returns
    -------
    tuple of int
        Non-empty tuple of non-negative Python integers.
    """
    if isinstance(raw_entropy, bool) or type(raw_entropy) is bool:
        raise ValueError(
            "SeedSequence entropy must not be a bool. "
            f"Got {raw_entropy!r}."
        )
    if type(raw_entropy) is int:
        single_word = _require_nonnegative_python_int(
            raw_entropy,
            field_name="SeedSequence entropy",
        )
        return (single_word,)
    if isinstance(raw_entropy, numbers.Integral):
        numpy_scalar_word = _require_nonnegative_python_int(
            raw_entropy,
            field_name="SeedSequence entropy",
        )
        return (numpy_scalar_word,)
    if type(raw_entropy) is str:
        raise ValueError(
            "SeedSequence entropy must be a non-negative integer or an "
            "iterable of integers, not a str. A string would be read "
            "character by character."
        )
    if type(raw_entropy) is bytes:
        raise ValueError(
            "SeedSequence entropy must be a non-negative integer or an "
            "iterable of integers, not bytes."
        )
    if type(raw_entropy) is bytearray:
        raise ValueError(
            "SeedSequence entropy must be a non-negative integer or an "
            "iterable of integers, not a bytearray."
        )
    if type(raw_entropy) is dict:
        raise ValueError(
            "SeedSequence entropy must be a non-negative integer or an "
            "iterable of integers, not a dict."
        )

    raw_word_list = []
    try:
        for raw_word in raw_entropy:
            raw_word_list.append(raw_word)
    except TypeError as iteration_error:
        raise ValueError(
            "SeedSequence entropy must be a non-negative integer or an "
            "iterable of integers. "
            f"Got type {type(raw_entropy).__name__}."
        ) from iteration_error
    raw_words = tuple(raw_word_list)

    normalized_words = []
    for raw_word in raw_words:
        python_word = _require_nonnegative_python_int(
            raw_word,
            field_name="SeedSequence entropy word",
        )
        normalized_words.append(python_word)

    if len(normalized_words) == 0:
        raise ValueError(
            "SeedSequence entropy is empty. The stored internal entropy "
            "must contain at least one non-negative integer word."
        )
    return tuple(normalized_words)


def keyed_uniform_value(internal_entropy, domain, key_parts):
    """Return one uniform value in ``[0.0, 1.0)`` for a research event key.

    This is a pure function. It does not consume ``World.rng`` or
    ``World.order_control_rng``, does not store a generator, and does not
    advance an attempt counter. The attempt number, when one is needed,
    is supplied by the caller as a key part.

    Parameters
    ----------
    internal_entropy : tuple of int
        Normalized entropy saved when the World was created.
    domain : str
        Non-empty event family, such as a future origin-choice or
        arrival-tiebreaker name. The same key parts in two domains are
        different events.
    key_parts : tuple
        Ordered parts. Each part is a non-empty ``str`` or a non-negative
        ``int``. ``bool`` is not an integer part.

    Returns
    -------
    float
        Value ``u`` with ``0.0 <= u < 1.0``.
    """
    checked_entropy = _check_internal_entropy(internal_entropy)
    checked_domain = _check_domain(domain)
    checked_key_parts = _check_key_parts(key_parts)
    serialized_material = _serialize_keyed_material(
        checked_entropy,
        checked_domain,
        checked_key_parts,
    )
    digest = _sha256_digest(serialized_material)
    return _uniform_value_from_digest(digest)


def _check_internal_entropy(internal_entropy):
    """Reject entropy that is not the stored tuple-of-ints form."""
    if isinstance(internal_entropy, bool) or type(internal_entropy) is not tuple:
        raise ValueError(
            "Internal entropy must be a tuple of non-negative Python ints. "
            f"Got type {type(internal_entropy).__name__}."
        )
    if len(internal_entropy) == 0:
        raise ValueError(
            "Internal entropy must contain at least one non-negative integer."
        )
    checked_words = []
    for word in internal_entropy:
        checked_word = _require_nonnegative_python_int(
            word,
            field_name="internal entropy word",
        )
        checked_words.append(checked_word)
    return tuple(checked_words)


def _check_domain(domain):
    """A domain names the research event family and must be a non-empty str."""
    if type(domain) is not str:
        raise ValueError(
            "Keyed uniform domain must be a non-empty str. "
            f"Got type {type(domain).__name__}."
        )
    if domain == "":
        raise ValueError(
            "Keyed uniform domain must be a non-empty str. An empty domain "
            "would let different event families share one key."
        )
    return domain


def _check_key_parts(key_parts):
    """Check ordered key parts once, before serialization."""
    if type(key_parts) is not tuple:
        raise ValueError(
            "Key parts must be a tuple in key order. "
            f"Got type {type(key_parts).__name__}."
        )
    if len(key_parts) == 0:
        raise ValueError(
            "Key parts must contain at least one non-empty str or a "
            "non-negative Python int. An empty tuple would hide missing "
            "Vehicle, Link, Node, visit, or attempt identifiers. Use a "
            "separate helper later for ordinary-merge seed derivation "
            "from entropy and domain alone."
        )
    checked_parts = []
    part_index = 0
    for key_part in key_parts:
        if type(key_part) is str:
            if key_part == "":
                raise ValueError(
                    f"Key part {part_index} is an empty str. Empty strings "
                    "are rejected so a missing name cannot look like a real id."
                )
            checked_parts.append(key_part)
        elif type(key_part) is bool:
            raise ValueError(
                f"Key part {part_index} is bool {key_part!r}. "
                "A visit number or attempt number must be a non-negative "
                "Python int, not True or False."
            )
        elif type(key_part) is int:
            if key_part < 0:
                raise ValueError(
                    f"Key part {part_index} is negative int {key_part}. "
                    "Visit numbers and attempt numbers must be non-negative."
                )
            checked_parts.append(key_part)
        else:
            raise ValueError(
                f"Key part {part_index} has unsupported type "
                f"{type(key_part).__name__}. Expected a non-empty str or "
                "a non-negative Python int."
            )
        part_index += 1
    return tuple(checked_parts)


def _require_nonnegative_python_int(raw_value, field_name):
    """Convert one integer word and reject bools and negatives.

    NumPy integer scalars are converted with ``int`` so the stored entropy
    does not keep a NumPy dtype. ``bool`` is rejected before that conversion
    because ``int(True)`` would silently become ``1``.
    """
    if isinstance(raw_value, bool) or type(raw_value) is bool:
        raise ValueError(
            f"{field_name} must be a non-negative integer, not bool "
            f"{raw_value!r}."
        )
    if type(raw_value) is int:
        python_value = raw_value
    elif isinstance(raw_value, numbers.Integral):
        # SeedSequence stores words as NumPy integer scalars. Those are not
        # Python int, but they are exact integers. float is not Integral, so
        # this does not truncate a fractional value.
        python_value = int(raw_value)
        if type(python_value) is not int:
            raise ValueError(
                f"{field_name} did not convert to a Python int. "
                f"Got type {type(python_value).__name__}."
            )
    else:
        raise ValueError(
            f"{field_name} must be a non-negative integer. "
            f"Got type {type(raw_value).__name__} value {raw_value!r}."
        )
    if python_value < 0:
        raise ValueError(
            f"{field_name} must be non-negative. Got {python_value}."
        )
    return python_value


def _serialize_keyed_material(internal_entropy, domain, key_parts):
    """Encode entropy, domain, and key parts with explicit boundaries.

    The bytes are not a public wire format. Tests use them to show that
    different keys do not collapse to the same byte string.

    Layout, all multi-byte integers big-endian:
    fixed prefix, entropy field, domain field, key-part count, key parts.
    A string records its UTF-8 length before its bytes, so ``("ab", "c")``
    is not the same as ``("a", "bc")``. An integer records its magnitude
    length before its bytes, so ``(1, 23)`` is not the same as ``(12, 3)``.
    The string ``"1"`` uses the string type tag and the integer ``1`` uses
    the integer type tag.
    """
    serialized = bytearray()
    serialized.extend(FORMAT_PREFIX)
    _append_entropy_field(serialized, internal_entropy)
    _append_domain_field(serialized, domain)
    _append_uint64(serialized, len(key_parts))
    for key_part in key_parts:
        _append_key_part(serialized, key_part)
    return bytes(serialized)


def _append_entropy_field(serialized, internal_entropy):
    serialized.extend(FIELD_ENTROPY)
    _append_uint64(serialized, len(internal_entropy))
    for entropy_word in internal_entropy:
        _append_nonnegative_int_payload(serialized, entropy_word)


def _append_domain_field(serialized, domain):
    serialized.extend(FIELD_DOMAIN)
    _append_utf8_text(serialized, domain)


def _append_key_part(serialized, key_part):
    if type(key_part) is str:
        serialized.extend(TYPE_STRING)
        _append_utf8_text(serialized, key_part)
        return
    serialized.extend(TYPE_NONNEGATIVE_INT)
    serialized.extend(SIGN_NONNEGATIVE)
    _append_nonnegative_int_payload(serialized, key_part)


def _append_utf8_text(serialized, text):
    text_bytes = text.encode("utf-8")
    _append_uint64(serialized, len(text_bytes))
    serialized.extend(text_bytes)


def _append_nonnegative_int_payload(serialized, value):
    magnitude_bytes = _nonnegative_int_to_big_endian_bytes(value)
    _append_uint64(serialized, len(magnitude_bytes))
    serialized.extend(magnitude_bytes)


def _nonnegative_int_to_big_endian_bytes(value):
    bit_length = value.bit_length()
    if bit_length == 0:
        byte_length = 1
    else:
        byte_length = (bit_length + 7) // 8
    return value.to_bytes(byte_length, byteorder="big", signed=False)


def _append_uint64(serialized, value):
    serialized.extend(value.to_bytes(8, byteorder="big", signed=False))


def _sha256_digest(serialized_material):
    """Hash the serialized key. SHA-256 is deterministic across processes."""
    hasher = hashlib.sha256()
    hasher.update(serialized_material)
    digest = hasher.digest()
    if len(digest) != DIGEST_SIZE_BYTES:
        raise RuntimeError(
            f"{HASH_ALGORITHM_NAME} digest length is {len(digest)}, "
            f"expected {DIGEST_SIZE_BYTES}."
        )
    return digest


def _uniform_value_from_digest(digest):
    """Map a digest to ``[0.0, 1.0)`` with an explicit 53-bit integer.

    The first 8 digest bytes are read as a big-endian integer. The top 53
    bits are kept. Dividing by ``2**53`` cannot produce ``1.0`` because the
    largest 53-bit integer is ``2**53 - 1``. No NumPy Generator is created,
    and no World RNG stream is advanced.
    """
    digest_prefix = digest[:UNIFORM_BYTE_COUNT]
    integer_64 = int.from_bytes(digest_prefix, byteorder="big", signed=False)
    uniform_integer = integer_64 >> UNIFORM_SHIFT
    divisor = 1 << UNIFORM_BIT_COUNT
    uniform_value = uniform_integer / divisor
    if uniform_value < 0.0 or uniform_value >= 1.0:
        raise RuntimeError(
            "Keyed uniform value fell outside [0.0, 1.0). "
            f"Got {uniform_value!r} from integer {uniform_integer}."
        )
    return uniform_value
