/// Reuses the original policy/seal/review/ledger logic, with a separate agent route.
Class pbp.Demo.Process Extends pbp.Process.Decide
{
Method DecisionTarget(Output live As %Boolean) As %String
{
    Set live=##class(pbp.Demo.Runtime).Allows(..CaseId)
    Quit $SELECT(live:"pbp.Demo.Operation",1:"")
}
}
