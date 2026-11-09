// Restricted, reproducible disk-bank Song Save callback trace.
// @category RolandD20
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import java.nio.file.*;
public class D20TraceSongSave extends GhidraScript {
 public void run() throws Exception {
  MemoryBlock b=currentProgram.getMemory().getBlock("CANDIDATE_85_18_08");
  if(b==null || b.getSize()!=0x3000)throw new IllegalStateException("Research project disk overlay required");
  AddressSet range=new AddressSet(b.getStart(),b.getEnd());
  int[] seeds={0x52be,0x52cb,0x52e1,0x52f1,0x5329,0x5f16,0x5ef0,0x5ecc,0x5ea9,0x53b5,0x5468,0x553f,0x6606,0x6008,0x6054,0x6018,0x600d,0x5e6d,0x6785,0x6877,0x6294,0x5e20,0x5e40,0x5814,0x5e49,0x588a,0x5873,0x5e5b,0x5f80,0x6653,0x66c5,0x67ef,0x676e,0x5810,0x5807,0x580c,0x5812,0x65b6,0x6841,0x69a2,0x670c,0x6804,0x5f60,0x602a};
  for(int v:seeds){Address a=b.getStart().getAddressSpace().getAddress(v);DisassembleCommand d=new DisassembleCommand(a,range,true);d.enableCodeAnalysis(false);d.applyTo(currentProgram,monitor);}
  StringBuilder s=new StringBuilder("Song Save candidate callbacks; disk bank 85/18/08; untraversed branches unresolved\n");
  for(int[] p:new int[][]{{0x51a5,0x6a00}}){for(InstructionIterator it=currentProgram.getListing().getInstructions(new AddressSet(b.getStart().getAddressSpace().getAddress(p[0]),b.getStart().getAddressSpace().getAddress(p[1])),true);it.hasNext();){Instruction i=it.next();s.append(i.getAddress()).append(' ').append(i).append('\n');}}
  Files.writeString(Path.of(getScriptArgs()[0]),s);
 }
}
