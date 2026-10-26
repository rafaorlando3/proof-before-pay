/// Proof Before Pay production: intake -> decision process -> agent / witness / test ledger / human workflow.
Class pbp.Production Extends Ens.Production
{

XData ProductionDefinition
{
<Production Name="pbp.Production" TestingEnabled="true" LogGeneralTraceEvents="false">
  <Description>Proof Before Pay: an AI Hub agent decides payment exceptions; every decision is sealed before any effect.</Description>
  <ActorPoolSize>2</ActorPoolSize>
  <Item Name="pbp.Service.Intake" Category="" ClassName="pbp.Service.Intake" PoolSize="0" Enabled="true" Foreground="false" Comment="Adapterless entry point (REST and demo feeder)" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="TargetConfigName">pbp.Process.Decide</Setting>
  </Item>
  <Item Name="pbp.Process.Decide" Category="" ClassName="pbp.Process.Decide" PoolSize="1" Enabled="true" Foreground="false" Comment="Rules, agent, seal, permit, human, ledger" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="AgentTarget">pbp.Operation.Agent</Setting>
    <Setting Target="Host" Name="ReplayTarget">pbp.Operation.Replay</Setting>
    <Setting Target="Host" Name="WitnessTarget">pbp.Operation.Witness</Setting>
    <Setting Target="Host" Name="LedgerTarget">pbp.Operation.TestLedger</Setting>
    <Setting Target="Host" Name="WorkflowTarget">pbp.Workflow</Setting>
    <Setting Target="Host" Name="PermitValiditySeconds">600</Setting>
    <Setting Target="Host" Name="AutonomousEffects">0</Setting>
    <Setting Target="Host" Name="MaxHumanRounds">3</Setting>
  </Item>
  <Item Name="pbp.Operation.Agent" Category="" ClassName="pbp.Operation.Agent" PoolSize="1" Enabled="false" Foreground="false" Comment="LIVE AI Hub agent via EnsLib.AI.Agent.OutboundAdapter (enabled by pbp.Setup when a provider key exists)" LogTraceEvents="false" Schedule="">
    <Setting Target="Adapter" Name="AgentClass">pbp.Agent</Setting>
    <Setting Target="Adapter" Name="AuthPolicy">pbp.AuthPolicy</Setting>
    <Setting Target="Adapter" Name="AuditPolicy">pbp.AuditPolicy</Setting>
    <Setting Target="Host" Name="FailureTimeout">120</Setting>
    <Setting Target="Host" Name="RetryInterval">5</Setting>
  </Item>
  <Item Name="pbp.Operation.Replay" Category="" ClassName="pbp.Operation.Replay" PoolSize="1" Enabled="true" Foreground="false" Comment="Recorded decisions (no key): honest replay, labelled in every seal" LogTraceEvents="false" Schedule="">
  </Item>
  <Item Name="pbp.Operation.Witness" Category="" ClassName="pbp.Operation.Witness" PoolSize="1" Enabled="true" Foreground="false" Comment="Seals records through ProofBeforePay.Witness" LogTraceEvents="false" Schedule="">
  </Item>
  <Item Name="pbp.Operation.TestLedger" Category="" ClassName="pbp.Operation.TestLedger" PoolSize="1" Enabled="true" Foreground="false" Comment="Test ledger: single-use permits, idempotent effects" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="FailureMode">none</Setting>
    <Setting Target="Host" Name="FailureTimeout">30</Setting>
  </Item>
  <Item Name="pbp.Workflow" Category="" ClassName="EnsLib.Workflow.Operation" PoolSize="1" Enabled="true" Foreground="false" Comment="Native human task: reviewer approves or rejects" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="AutoCreateRole">1</Setting>
  </Item>
</Production>
}

}
