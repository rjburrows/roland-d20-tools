// Disassemble selected MCS-96 A/B mainboard PROM ranges around rhythm records.
// @category RolandD20
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import ghidra.program.model.symbol.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.HexFormat;

public class D20TraceABPatternReader extends GhidraScript {
 public void run() throws Exception {
  if (!currentProgram.getLanguageID().toString().equals("MCS96:LE:16:default"))
   throw new IllegalStateException("Expected Intel MCS-96 language");
  MemoryBlock block=currentProgram.getMemory().getBlock(currentProgram.getMinAddress());
  if (block==null || block.getSize()!=65536)
   throw new IllegalStateException("Expected 64 KiB B/A interleaved raw ROM at address zero");
  byte[] bytes=new byte[65536];
  currentProgram.getMemory().getBytes(block.getStart(),bytes);
  String digest=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
  if (!digest.equals("283cda5527d3b21cc39093cdcb0f982f0399466585b871b9fa77ac3ae855f2ca"))
   throw new IllegalStateException("Unexpected A/B image: "+digest);
  StringBuilder out=new StringBuilder("Interleaved B/A ROM SHA256 "+digest+"\n"
    +"MCS-96 disassembly; file offsets treated as CPU addresses provisionally.\n\n");
  AddressSet set=new AddressSet(block.getStart(),block.getEnd());
  int[][] spans={{0x1200,0x122f},{0x1230,0x125d},
                 {0x1301,0x1318},{0x13bd,0x1406},{0x1538,0x155f},
                 {0x15fc,0x161e},{0x1683,0x16bc},{0x16a2,0x16da},
                 {0x16ed,0x173b},{0x1882,0x1891},{0x1894,0x18e0},
                 {0x1910,0x19d0},{0x1a6d,0x1ae0},{0x1ae5,0x1b8f},
                 {0x1b82,0x1b8f},
                 {0x1cb4,0x1cd9},{0x1ceb,0x1cfc},{0x2080,0x20ef},
                 {0x4a58,0x4a80},{0x55d3,0x55f9},{0x6cd0,0x6cf2},
                 {0x6dac,0x6e0f},{0x6e56,0x6eac}};
  for(int[] span:spans) {
   Address start=block.getStart().add(span[0]);
   Address end=block.getStart().add(span[1]);
   DisassembleCommand command=new DisassembleCommand(start,set,true);
   command.enableCodeAnalysis(false);
   boolean ok=command.applyTo(currentProgram,monitor);
   out.append(String.format("[%04X-%04X] decoded=%s\n",span[0],span[1],ok));
   for(InstructionIterator it=currentProgram.getListing().getInstructions(
           new AddressSet(start,end),true);it.hasNext();) {
    Instruction ins=it.next();
    out.append(ins.getAddress()).append(' ').append(ins).append('\n');
   }
   out.append('\n');
  }
  out.append("[Inbound flow and data references; discovered in this research copy]\n");
  for(int target:new int[]{0x1230,0x16ed,0x16f0,0x1713,0x1717,0x1724,0x1882,0x1894,
                             0x1b91,0x1b99,0x1bc9,0x9700,0x9740,0xb000}) {
   Address address=block.getStart().add(target);
   out.append(String.format("%04X:",target));
   for(Reference reference:currentProgram.getReferenceManager().getReferencesTo(address)) {
    Instruction source=currentProgram.getListing().getInstructionContaining(reference.getFromAddress());
    out.append(" ").append(reference.getFromAddress()).append("(")
       .append(reference.getReferenceType()).append(")")
       .append(source==null?"":":"+source);
   }
   out.append('\n');
  }
  long instructionCount=0;
  for(InstructionIterator it=currentProgram.getListing().getInstructions(true);it.hasNext();){
   it.next();instructionCount++;
  }
  out.append("Total disassembled instructions: ").append(instructionCount).append('\n');
  Files.writeString(Path.of(getScriptArgs()[0]),out);
  if(getScriptArgs().length>1) {
   StringBuilder listing=new StringBuilder("Decoded MCS-96 research copy; instruction inventory.\n");
   for(InstructionIterator it=currentProgram.getListing().getInstructions(
     new AddressSet(block.getStart(),block.getEnd()),true);
     it.hasNext();) {
    Instruction ins=it.next();
    listing.append(ins.getAddress()).append(' ').append(ins).append('\n');
   }
   Files.writeString(Path.of(getScriptArgs()[1]),listing);
  }
  println("Exported " + getScriptArgs()[0]);
 }
}
