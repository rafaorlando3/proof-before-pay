/// Tool set exposed to the decision agent: only the read-only case tools.
Class pbp.ToolSet Extends %AI.ToolSet [ DependsOn = pbp.Tools ]
{

XData Definition
{
<ToolSet Name="pbp.ToolSet">
  <Include Class="pbp.Tools"/>
</ToolSet>
}

}
