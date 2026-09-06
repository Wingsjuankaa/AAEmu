// @category AA10
import ghidra.app.script.GhidraScript;
import java.nio.file.*;
public class Aa10IpnyaSymbols extends GhidraScript {
 public void run() throws Exception {
  String needle=getScriptArgs().length>1?getScriptArgs()[1].toLowerCase():"equipslotreinforce";
  StringBuilder b=new StringBuilder();
  b.append("sha256=").append(currentProgram.getExecutableSHA256()).append(" base=").append(currentProgram.getImageBase()).append("\n");
  var syms=currentProgram.getSymbolTable().getAllSymbols(true);
  while(syms.hasNext()) {var s=syms.next(); if(s.getName(true).toLowerCase().contains(needle)) b.append("SYM ").append(s.getAddress()).append(" ").append(s.getName(true)).append("\n");}
  var data=currentProgram.getListing().getDefinedData(true);
  while(data.hasNext()) {var d=data.next(); var v=d.getValue(); if(!(v instanceof String))continue;String s=((String)v).toLowerCase(); if(!s.contains(needle)&&!(needle.equals("equipslotreinforce")&&s.contains("slot_reinforce")))continue;
   b.append("STR ").append(d.getAddress()).append(" ").append(v).append("\n");
   for(var r:getReferencesTo(d.getAddress())) {var f=getFunctionContaining(r.getFromAddress());b.append(" REF ").append(r.getFromAddress()).append(" ").append(f==null?"none":f.getEntryPoint()).append("\n");}
  }
  Files.writeString(Path.of(getScriptArgs()[0]),b);println("Exported chars="+b.length());
 }
}
