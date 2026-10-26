/// Shared helpers for Proof Before Pay: UTC timestamps in pbp.seal/1 format, SHA-256 hex,
/// safe JSON access and a persistent log where every failure keeps its reason.
Class pbp.Util Extends %RegisteredObject
{

/// Current UTC time as "YYYY-MM-DDThh:mm:ss.mmmZ" (exactly 3 decimals, as pbp.seal/1 requires).
ClassMethod NowISO() As %String
{
    Set ts = $ZTIMESTAMP
    Set d = $ZDATE(+ts, 3)
    Set sec = $PIECE(ts, ",", 2)
    Set t = $ZTIME(sec, 1, 3)
    Quit d _ "T" _ t _ "Z"
}

/// Convert an ISO timestamp produced by NowISO back to $HOROLOG-like seconds (UTC) for ordering.
ClassMethod ISOToSeconds(iso As %String) As %Numeric
{
    Set out = -1
    Try {
        Set d = $PIECE(iso, "T", 1)
        Set t = $PIECE($PIECE(iso, "T", 2), "Z", 1)
        Set h = $ZDATEH(d, 3)
        Set s = $ZTIMEH($PIECE(t, ".", 1), 1)
        Set ms = +("0." _ $PIECE(t, ".", 2))
        Set out = (h * 86400) + s + ms
    } Catch ex {
        Set out = -1
    }
    Quit out
}

/// Lowercase hex SHA-256 of a string (UTF-8).
ClassMethod SHA256Hex(data As %String) As %String
{
    Set bin = $SYSTEM.Encryption.SHAHash(256, $ZCONVERT(data, "O", "UTF8"))
    Quit $ZCONVERT(##class(%xsd.hexBinary).LogicalToXSD(bin), "L")
}

/// Random 32-byte hex identifier.
ClassMethod RandomHex(bytes As %Integer = 16) As %String
{
    Set bin = $SYSTEM.Encryption.GenCryptRand(bytes)
    Quit $ZCONVERT(##class(%xsd.hexBinary).LogicalToXSD(bin), "L")
}

/// Parse JSON safely. Returns "" and sets reason on failure (never throws).
ClassMethod ParseJSON(text As %String, Output reason As %String) As %DynamicAbstractObject
{
    Set reason = "", obj = ""
    Try {
        Set obj = ##class(%DynamicAbstractObject).%FromJSON(text)
    } Catch ex {
        Set reason = "invalid_json", obj = ""
    }
    Quit obj
}

/// Guard an incoming JSON text before anything is persisted: size, strict parse (duplicate keys refused),
/// depth, and the personal-data scanner of the sealing core. Returns "" when clean, else a stable reason.
/// Never returns offending values.
ClassMethod GuardJSON(text As %String, maxBytes As %Integer = 60000) As %String
{
    Set reason = ""
    Try {
        If $LENGTH(text) > maxBytes { Set reason = "input_too_large" }
        Else {
            Set guard = ##class(%SYS.Python).Import("pbp_guard.intake")
            Set reason = guard."check_json"(text, maxBytes)
        }
    } Catch ex {
        Set reason = "guard_unavailable"
        Do ..LogEx("pbp.Util.GuardJSON", ex)
    }
    Quit reason
}

/// Persistent log line. Message text may contain the exception reason; it never goes to a public reply.
ClassMethod Log(level As %String, where As %String, message As %String, caseId As %String = "") As %Status
{
    Set sc = $$$OK
    Try {
        Set row = ##class(pbp.Data.Log).%New()
        Set row.At = ..NowISO()
        Set row.Level = level
        Set row.Where = where
        Set row.Message = $EXTRACT(..Sanitize(message), 1, 4000)
        Set row.CaseId = caseId
        Set sc = row.%Save()
    } Catch ex {
        Set sc = ex.AsStatus()
    }
    Quit sc
}

/// Log an exception WITHOUT its data: name, code and code location only. ex.Data and DisplayString may carry
/// personal data or secrets (the Witness smoke proves it), so they are never stored.
ClassMethod LogEx(where As %String, ex As %Exception.AbstractException, caseId As %String = "") As %Status
{
    Set text = "exception " _ ex.Name _ " code=" _ ex.Code _ " at " _ ex.Location
    Quit ..Log("error", where, text, caseId)
}

/// Remove things that look like secrets or personal data from a diagnostic line (keys, e-mails, long digit runs).
ClassMethod Sanitize(text As %String) As %String
{
    Set t = text
    Set t = ##class(%Regex.Matcher).%New("(?i)(api[_-]?key|token|secret|password|bearer)[^\s]*", t).ReplaceAll("$1=[redacted]")
    Set t = ##class(%Regex.Matcher).%New("[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+", t).ReplaceAll("[email]")
    Set t = ##class(%Regex.Matcher).%New("[0-9][0-9.\-/ ]{9,}[0-9]", t).ReplaceAll("[digits]")
    Set t = ##class(%Regex.Matcher).%New("\b[A-Za-z0-9_-]{32,}\b", t).ReplaceAll("[long-token]")
    Quit t
}

/// Status text for logs.
ClassMethod StatusText(sc As %Status) As %String
{
    Quit $SYSTEM.Status.GetErrorText(sc)
}

/// Read an environment variable with default.
ClassMethod Env(name As %String, default As %String = "") As %String
{
    Set v = $SYSTEM.Util.GetEnviron(name)
    Quit $SELECT(v = "": default, 1: v)
}

/// Digits-only check for minor amounts ("0" or no leading zero), as pbp.seal/1 requires.
ClassMethod IsMinorAmount(v As %String) As %Boolean
{
    Quit $MATCH(v, "(0|[1-9][0-9]{0,17})")
}

}
