package pbp.pex;

import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/** Checks the exact UTF-8 bytes of a synthetic evidence export, not its authority. */
public final class ExportDigest {
    public static final int MAX_BYTES = 65536;
    private ExportDigest() {}

    public static final class Result {
        public final String status;
        public final String sha256;
        public final int bytes;
        Result(String status, String sha256, int bytes) {
            this.status = status; this.sha256 = sha256; this.bytes = bytes;
        }
    }

    public static Result inspect(String payload, String expected) throws Exception {
        if (payload == null)
            return new Result("INVALID_PAYLOAD", "", 0);
        if (expected == null || !expected.matches("[0-9a-f]{64}"))
            return new Result("INVALID_EXPECTED_DIGEST", "", 0);
        final byte[] bytes;
        try {
            ByteBuffer encoded = StandardCharsets.UTF_8.newEncoder()
                .onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT).encode(java.nio.CharBuffer.wrap(payload));
            bytes = new byte[encoded.remaining()]; encoded.get(bytes);
        } catch (CharacterCodingException e) {
            return new Result("INVALID_UTF8", "", 0);
        }
        if (bytes.length > MAX_BYTES) return new Result("PAYLOAD_TOO_LARGE", "", bytes.length);
        byte[] digest = MessageDigest.getInstance("SHA-256").digest(bytes);
        StringBuilder hex = new StringBuilder(64);
        for (byte value : digest) hex.append(String.format("%02x", value & 255));
        String actual = hex.toString();
        boolean equal = MessageDigest.isEqual(actual.getBytes(StandardCharsets.US_ASCII),
            expected.getBytes(StandardCharsets.US_ASCII));
        return new Result(equal ? "MATCH" : "MISMATCH", actual, bytes.length);
    }
}
