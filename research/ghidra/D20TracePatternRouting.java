// Follow all direct C 1.11 ROM references to the pattern-duration array B6D5.
// @category RolandD20
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.HexFormat;

public class D20TracePatternRouting extends GhidraScript {
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
   +"Normal C8/18/18 bank, selected direct B6D5 references; static code only.\n\n");
  // A previous bounded probe erroneously started decoding at 5800, which is
  // the immediate F3 byte of the LD A,F3 instruction starting at 57FF.
  if((rom[0x57ff]&255)!=0x3e||(rom[0x5800]&255)!=0xf3)
   throw new IllegalStateException("Unexpected F3 command bytes");
  Address wrong=normal.getStart().add(0x5800);
  Instruction mistaken=currentProgram.getListing().getInstructionAt(wrong);
  if(mistaken!=null&&mistaken.getMnemonicString().equals("DI")) {
   currentProgram.getListing().clearCodeUnits(wrong,wrong,false);
   out.append("Cleared stale standalone DI at 5800 (immediate of 57FF LD A,F3).\n\n");
  }
  AddressSet region=new AddressSet(normal.getStart(),normal.getEnd());
  for(int[] span:new int[][]{{0x1420,0x14ae},{0x1580,0x1699},
    {0x1880,0x18b5},{0x19d2,0x19de},{0x19df,0x19f8},
    {0x4a79,0x4ac1},{0x4c86,0x4c9d},
    {0x5225,0x5265},{0x551f,0x5568},
    {0x5710,0x5777},{0x57ff,0x5800},{0x57e0,0x5895},
    {0x5da1,0x5e05},{0x7640,0x7688},
    {0x5070,0x50a4}}){
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
  Files.writeString(Path.of(getScriptArgs()[0]),out);
  println("Exported " + getScriptArgs()[0]);
 }
}
