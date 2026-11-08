/// Separate optional production: export transport inspection only, no financial workflow.
Class pbp.PEX.Production Extends Ens.Production
{
XData ProductionDefinition
{
<Production Name="pbp.PEX.Production" TestingEnabled="false" LogGeneralTraceEvents="false">
  <Description>Java PEX verification of exact synthetic evidence-export bytes.</Description>
  <ActorPoolSize>1</ActorPoolSize>
  <Item Name="pbp.PEX.Intake" ClassName="pbp.PEX.Intake" PoolSize="0" Enabled="true" />
  <Item Name="pbp.PEX.ExportDigest" ClassName="pbp.PEX.ExportDigestOperation" PoolSize="1" Enabled="true">
    <Setting Target="Host" Name="FailureTimeout">10</Setting>
    <Setting Target="Host" Name="RetryInterval">1</Setting>
  </Item>
</Production>
}
}
