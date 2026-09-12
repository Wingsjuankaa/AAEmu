import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.util.*;
public class FindGardenScore extends GhidraScript {
 public void run() throws Exception {
  Set<Function> fs=new LinkedHashSet<>();
  for(Function f:currentProgram.getFunctionManager().getFunctions(true))
   if(f.getName(true).toLowerCase().contains("zonescore")){println("SYMBOL "+f.getName(true)+" "+f.getEntryPoint());fs.add(f);}
  DataIterator ds=currentProgram.getListing().getDefinedData(true);
  while(ds.hasNext()) {Data d=ds.next(); Object v=d.getValue(); if(v instanceof String && (((String)v).contains("ZoneScore") || ((String)v).contains("zone_score") || ((String)v).contains("skill_urk_zone"))) {
   println("STRING "+d.getAddress()+" "+v);
   for(Reference r:getReferencesTo(d.getAddress())){Function f=getFunctionContaining(r.getFromAddress());if(f!=null){println("REF "+f.getEntryPoint()+" "+f.getName(true));fs.add(f);}}
  }}
  DecompInterface dc=new DecompInterface();dc.openProgram(currentProgram);
  for(Function f:fs){println("FUNCTION "+f.getEntryPoint()+" "+f.getName(true));DecompileResults r=dc.decompileFunction(f,60,monitor);if(r.decompileCompleted())println(r.getDecompiledFunction().getC());}dc.dispose();
 }
}
