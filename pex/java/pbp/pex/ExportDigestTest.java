package pbp.pex;

public final class ExportDigestTest {
    private static int checks;
    private static void check(boolean ok) { if (!ok) throw new AssertionError("check " + checks); checks++; }
    public static void main(String[] args) throws Exception {
        String abc = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";
        check(ExportDigest.inspect("abc", abc).status.equals("MATCH"));
        check(ExportDigest.inspect("abd", abc).status.equals("MISMATCH"));
        check(ExportDigest.inspect("", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855").status.equals("MATCH"));
        check(ExportDigest.inspect("abc", "bad").status.equals("INVALID_EXPECTED_DIGEST"));
        check(ExportDigest.inspect("abc", abc.toUpperCase()).status.equals("INVALID_EXPECTED_DIGEST"));
        check(ExportDigest.inspect(null, abc).status.equals("INVALID_PAYLOAD"));
        check(ExportDigest.inspect("\ud800", abc).status.equals("INVALID_UTF8"));
        check(ExportDigest.inspect(new String(new char[65537]), abc).status.equals("PAYLOAD_TOO_LARGE"));
        String unicode = "ação 漢字 💡";
        ExportDigest.Result u = ExportDigest.inspect(unicode, abc);
        check(u.bytes == unicode.getBytes(java.nio.charset.StandardCharsets.UTF_8).length);
        check(ExportDigest.inspect(unicode, u.sha256).status.equals("MATCH"));
        String multi = new String(new char[40000]).replace('\0', '漢');
        check(ExportDigest.inspect(multi, abc).status.equals("PAYLOAD_TOO_LARGE"));
        check(!ExportDigest.inspect("abc\n", abc).status.equals("MATCH"));
        System.out.println("ExportDigest checks=" + checks + " PASS");
    }
}
