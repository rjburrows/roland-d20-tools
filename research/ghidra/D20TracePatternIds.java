// Export C 1.11 ROM evidence for rhythm pattern ID display and duration lookup.
// @category RolandD20
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.HexFormat;

public class D20TracePatternIds extends GhidraScript {
 public void run() throws Exception {
  Memory memory=currentProgram.getMemory();
  MemoryBlock raw=memory.getBlock("ROM_FILE_REFERENCE");
  MemoryBlock normal=memory.getBlock("ROM_NORMAL_0000_7FFF");
  if(raw==null||raw.getSize()!=65536||normal==null||normal.getSize()!=0x8000)
   throw new IllegalStateException("Expected mapped C 1.11 research copy");
  byte[] rom=new byte[65536];memory.getBytes(raw.getStart(),rom);
  String hash=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(rom));
  if(!hash.equals("7c8d2aecbb74bf939661d3fd904c691a4c7c749a374cb804c0247b64b649e1c2"))
   throw new IllegalStateException("Unexpected ROM: "+hash);
  StringBuilder out=new StringBuilder("C 1.11 ROM SHA256 "+hash+"\n"
   +"Normal C8/18/18 bank; static instructions, no runtime RAM image.\n\n");
  AddressSet region=new AddressSet(normal.getStart(),normal.getEnd());
  for(int[] span:new int[][]{{0x077b,0x0793},{0x47f4,0x4840},{0x5e06,0x5e25}}){
   Address start=normal.getStart().add(span[0]);
   Address end=normal.getStart().add(span[1]);
   DisassembleCommand command=new DisassembleCommand(start,region,true);
   command.enableCodeAnalysis(false);
   command.applyTo(currentProgram,monitor);
   out.append(String.format("[%04X-%04X]\n",span[0],span[1]));
   for(InstructionIterator it=currentProgram.getListing().getInstructions(new AddressSet(start,end),true);it.hasNext();){
    Instruction instruction=it.next();
    out.append(instruction.getAddress()).append(' ').append(instruction).append('\n');
   }
   out.append('\n');
  }
  out.append("Duration words at 5EAA: ");
  for(int i=0;i<9;i++){
   int p=0x5eaa+2*i;
   out.append((rom[p]&255)|((rom[p+1]&255)<<8)).append(i==8?'\n':',');
  }
  out.append("Sample-derived candidate mapping (NOT established by ROM address arithmetic):\n"
   +"IDs 20..3F -> 32 saved blocks; ID 3E -> block 30, ID 3F -> block 31.\n");
  Files.writeString(Path.of(getScriptArgs()[0]),out);
  println("Exported " + getScriptArgs()[0]);
 }
}
