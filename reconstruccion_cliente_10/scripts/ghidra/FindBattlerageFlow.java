// Read-only native index for Tiger Strike movement and combat/passive resources.
import ghidra.app.script.GhidraScript;
public class FindBattlerageFlow extends GhidraScript {
 boolean match(String s) { s=s.toLowerCase(); return s.contains("parry")||s.contains("bufflearned")||s.contains("passivebuff")||s.contains("plot")||s.contains("leapskill")||s.contains("skillcontrollerleap")||s.contains("skillcontrollerturn")||s.contains("combatre")||s.contains("combat_resource")||s.contains("use_exe_time")||s.contains("off_passive")||s.contains("executiontime")||s.contains("exetime"); }
 public void run() throws Exception {
  println("SHA256="+currentProgram.getExecutableSHA256()+" BASE="+currentProgram.getImageBase());
  var ss=currentProgram.getSymbolTable().getAllSymbols(true);
  while(ss.hasNext()&&!monitor.isCancelled()){var s=ss.next();if(match(s.getName(true)))println("SYMBOL "+s.getAddress()+" "+s.getName(true));}
  var ds=currentProgram.getListing().getDefinedData(true);
  while(ds.hasNext()&&!monitor.isCancelled()){var d=ds.next();if(!(d.getValue() instanceof String)||!match((String)d.getValue()))continue;println("STRING "+d.getAddress()+" "+d.getValue());for(var r:getReferencesTo(d.getAddress())){var f=getFunctionContaining(r.getFromAddress());println("REF "+r.getFromAddress()+" "+(f==null?"data":f.getName()+"@"+f.getEntryPoint()));}}
 }
}
