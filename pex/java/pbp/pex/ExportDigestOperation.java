package pbp.pex;

import com.intersystems.enslib.pex.BusinessOperation;
import com.intersystems.jdbc.IRISObject;

/** Read-only PEX operation. No provider, ledger, network, file or approval calls. */
public final class ExportDigestOperation extends BusinessOperation {
    @Override public void OnInit() {}
    @Override public void OnTearDown() {}
    @Override public Object OnMessage(Object message) throws Exception {
        if (!(message instanceof IRISObject)) throw new IllegalArgumentException("IRIS request required");
        IRISObject request = (IRISObject) message;
        ExportDigest.Result result = ExportDigest.inspect(request.getString("Payload"),
            request.getString("ExpectedSHA256"));
        IRISObject response = (IRISObject) request.iris.classMethodObject("pbp.PEX.InspectResponse", "%New");
        response.set("Status", result.status);
        response.set("SHA256", result.sha256);
        response.set("ByteCount", result.bytes);
        response.set("InspectionOnly", true);
        return response;
    }
}
