// Research-copy disassembly of bank transitions and explicit callback targets.
// @category RolandD20
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import java.nio.file.*;
public class D20TraceEntries extends GhidraScript {
 public void run() throws Exception {
  StringBuilder s=new StringBuilder();
  MemoryBlock low=currentProgram.getMemory().getBlock("ROM_NORMAL_0000_7FFF");
  MemoryBlock disk=currentProgram.getMemory().getBlock("CANDIDATE_85_18_08");
  for(int n=0;n<2;n++){
   MemoryBlock b=n==0?low:disk;
   AddressSet range=new AddressSet(b.getStart(),n==0?toAddr(0x4fff):b.getEnd());
   int[] seeds=n==0?new int[]{0x794,0x79e,0x3c85,0x3e3f,0x3e63}:new int[]{0x5071,0x51ca,0x5202,0x5214,0x5226,0x522b};
   for(int v:seeds){Address a=b.getStart().getAddressSpace().getAddress(v);DisassembleCommand d=new DisassembleCommand(a,range,true);d.enableCodeAnalysis(false);d.applyTo(currentProgram,monitor);}
   InstructionIterator it=currentProgram.getListing().getInstructions(range,true);
   while(it.hasNext()){Instruction i=it.next();long a=i.getAddress().getOffset();if(n==1||(a>=0x790&&a<0x7a8)||(a>=0x3c50&&a<0x3f00)) s.append(i.getAddress()).append(" ").append(i).append('\n');}
  }
  Files.writeString(Path.of(getScriptArgs()[0]),s);
 }
}
