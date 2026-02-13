"""
Reed-Solomon Error Correction Encoding.

Implements RS(N, K) encoding over GF(2^8) for DAB error protection.
Based on ODR-DabMux lib/ReedSolomon.cpp implementation.
"""
import structlog
from typing import List

logger = structlog.get_logger()


class ReedSolomonEncoder:
    """
    Reed-Solomon encoder for error correction.

    Implements RS(N, K) systematic encoding where:
    - N: Total codeword symbols (information + parity)
    - K: Information symbols
    - Parity symbols = N - K

    Uses Galois Field GF(2^8) with generator polynomial 0x11d.
    """

    # GF(2^8) parameters
    MM = 8          # Bits per symbol
    NN = 255        # Max codeword length for GF(2^8)

    # Generator polynomial (primitive polynomial for GF(2^8))
    GFPOLY = 0x11d

    def __init__(self, n: int, k: int) -> None:
        """
        Initialize Reed-Solomon encoder.

        Args:
            n: Total symbols (information + parity)
            k: Information symbols

        Raises:
            ValueError: If parameters are invalid
        """
        if n > self.NN:
            raise ValueError(f"n={n} must be <= {self.NN}")
        if k >= n:
            raise ValueError(f"k={k} must be < n={n}")
        if k <= 0:
            raise ValueError(f"k={k} must be > 0")

        self.n = n
        self.k = k
        self.nroots = n - k  # Number of parity symbols
        self.pad = self.NN - n  # Padding

        # Generate GF tables
        self._alpha_to: List[int] = [0] * (self.NN + 1)
        self._index_of: List[int] = [0] * (self.NN + 1)
        self._generate_gf_tables()

        # Generate generator polynomial
        self._genpoly: List[int] = [0] * (self.nroots + 1)
        self._generate_poly()

        logger.debug(
            "RS encoder initialized",
            n=self.n,
            k=self.k,
            parity=self.nroots
        )

    def _generate_gf_tables(self) -> None:
        """Generate Galois Field lookup tables."""
        # Generate alpha_to[] (powers of primitive element)
        # alpha_to[i] = alpha^i
        self._alpha_to[0] = 1

        for i in range(1, self.NN):
            self._alpha_to[i] = self._alpha_to[i - 1] << 1

            # If overflow, XOR with primitive polynomial
            if self._alpha_to[i] & (1 << self.MM):
                self._alpha_to[i] ^= self.GFPOLY

        self._alpha_to[self.NN] = 0

        # Generate index_of[] (discrete log)
        # index_of[alpha^i] = i
        self._index_of[0] = self.NN  # log(0) is undefined, use NN
        for i in range(self.NN):
            self._index_of[self._alpha_to[i]] = i

    def _generate_poly(self) -> None:
        """Generate generator polynomial for RS code."""
        # Generator polynomial g(x) = (x - alpha^0)(x - alpha^1)...(x - alpha^(nroots-1))
        # Start with g(x) = 1
        self._genpoly[0] = 1

        for i in range(self.nroots):
            # Multiply by (x - alpha^i)
            self._genpoly[i + 1] = 1

            # Multiply existing terms
            for j in range(i, 0, -1):
                if self._genpoly[j] != 0:
                    self._genpoly[j] = (
                        self._genpoly[j - 1] ^
                        self._alpha_to[self._modnn(self._index_of[self._genpoly[j]] + i)]
                    )
                else:
                    self._genpoly[j] = self._genpoly[j - 1]

            # Constant term
            self._genpoly[0] = self._alpha_to[self._modnn(self._index_of[self._genpoly[0]] + i)]

    def _modnn(self, x: int) -> int:
        """
        Modulo NN operation for GF indices.

        Args:
            x: Value to reduce

        Returns:
            x mod NN
        """
        while x >= self.NN:
            x -= self.NN
            x = (x >> self.MM) + (x & self.NN)
        return x

    def encode(self, data: bytes) -> bytes:
        """
        Encode data with Reed-Solomon parity.

        Args:
            data: Information bytes (length must be k)

        Returns:
            Parity bytes (length nroots)

        Raises:
            ValueError: If data length != k
        """
        if len(data) != self.k:
            raise ValueError(f"Data length {len(data)} must equal k={self.k}")

        # Initialize parity array
        parity = bytearray(self.nroots)

        # Encode
        for i in range(self.k):
            feedback = self._index_of[data[i] ^ parity[0]]

            if feedback != self.NN:  # feedback != 0
                # Shift and XOR with generator polynomial
                for j in range(self.nroots - 1):
                    parity[j] = parity[j + 1] ^ self._alpha_to[self._modnn(feedback + self._genpoly[self.nroots - j])]
                parity[self.nroots - 1] = self._alpha_to[self._modnn(feedback + self._genpoly[0])]
            else:
                # feedback == 0, just shift
                for j in range(self.nroots - 1):
                    parity[j] = parity[j + 1]
                parity[self.nroots - 1] = 0

        return bytes(parity)

    def encode_block(self, data: bytes) -> bytes:
        """
        Encode data block and return data + parity.

        Args:
            data: Information bytes (length must be k)

        Returns:
            Encoded block (data + parity, length n)
        """
        parity = self.encode(data)
        return data + parity


# Common RS configurations for DAB
class ReedSolomonDAB:
    """Predefined Reed-Solomon configurations for DAB."""

    @staticmethod
    def packet_mode() -> ReedSolomonEncoder:
        """
        RS encoder for packet mode.

        RS(204, 188): 188 information bytes, 16 parity bytes.
        Used for enhanced packet mode services.

        Returns:
            Configured RS encoder
        """
        return ReedSolomonEncoder(n=204, k=188)

    @staticmethod
    def edi_pft(n: int, k: int) -> ReedSolomonEncoder:
        """
        RS encoder for EDI/PFT.

        Variable configuration for Protection, Fragmentation, and Transport.

        Args:
            n: Total symbols
            k: Information symbols

        Returns:
            Configured RS encoder
        """
        return ReedSolomonEncoder(n=n, k=k)
