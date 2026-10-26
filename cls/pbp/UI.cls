/// Authenticated same-origin console, with UTF-8 and no-store response headers.
Class pbp.UI Extends %CSP.REST
{
Parameter CHARSET = "utf-8";
Parameter CONTENTTYPE = "text/html";
XData UrlMap [ XMLNamespace = "http://www.intersystems.com/urlmap" ]
{
<Routes>
<Route Url="/" Method="GET" Call="Index"/>
<Route Url="/index.html" Method="GET" Call="Index"/>
</Routes>
}
ClassMethod Index() As %Status
{
    Set %response.ContentType="text/html",%response.CharSet="utf-8"
    Do %response.SetHeader("Cache-Control","no-store")
    Do %response.SetHeader("X-Content-Type-Options","nosniff")
    Set stream=##class(%Stream.FileCharacter).%New()
    Set stream.TranslateTable="UTF8"
    Set sc=stream.LinkToFile($GET(^pbp.config("uiRoot"),"/opt/pbp/ui")_"/index.html")
    If $$$ISERR(sc) { Set %response.Status="503" Write "Console unavailable" Quit $$$OK }
    While 'stream.AtEnd { Write stream.Read(32000) }
    Quit $$$OK
}
}
