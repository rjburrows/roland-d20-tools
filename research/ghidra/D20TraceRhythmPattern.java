// Hash-checked, bounded static trace for D-20 rhythm pattern addressing.
// @category RolandD20
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.HexFormat;

public class D20TraceRhythmPattern extends GhidraScript {
 public void run() throws Exception {
  Memory mem=currentProgram.getMemory(); MemoryBlock raw=mem.getBlock("ROM_FILE_REFERENCE");
  MemoryBlock normal=mem.getBlock("ROM_NORMAL_0000_7FFF");
  if(raw==null||normal==null||raw.getSize()!=65536)throw new IllegalStateException("Wrong C ROM map");
  byte[] bytes=new byte[65536];mem.getBytes(raw.getStart(),bytes);
  String sha=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
  if(!sha.equals("7c8d2aecbb74bf939661d3fd904c691a4c7c749a374cb804c0247b64b649e1c2"))throw new IllegalStateException(sha);
  StringBuilder out=new StringBuilder("C 1.11 rhythm trace SHA256 "+sha+"\nNormal bank; static branches not proven at runtime.\n");
  AddressSet region=new AddressSet(normal.getStart(),normal.getEnd());
  int[][] spans={{0x295f,0x2ac0},{0x5540,0x55b5},{0x5726,0x5773},{0x5b13,0x5bb1},{0x5e06,0x5ea9},{0x5ffa,0x6056},{0x7654,0x76cc}};
  for(int[] span:spans){
   Address a=toAddr(span[0]);DisassembleCommand d=new DisassembleCommand(a,region,true);
   d.enableCodeAnalysis(false);d.applyTo(currentProgram,monitor);
   out.append(String.format("\n[%04X-%04X]\n",span[0],span[1]));
   for(InstructionIterator it=currentProgram.getListing().getInstructions(new AddressSet(a,toAddr(span[1])),true);it.hasNext();){
    Instruction ins=it.next();out.append(ins.getAddress()).append(' ').append(ins).append('\n');
   }
  }
  Files.writeString(Path.of(getScriptArgs()[0]),out);
  println("Rhythm evidence exported: "+getScriptArgs()[0]);
 }
}
