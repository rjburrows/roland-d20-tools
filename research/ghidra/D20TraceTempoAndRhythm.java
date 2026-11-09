// Export bounded timing and rhythm instructions from the hash-checked C 1.11 copy.
// Static views do not prove which bank or branches execute during a disk load.
// @category RolandD20
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.HexFormat;

public class D20TraceTempoAndRhythm extends GhidraScript {
 public void run() throws Exception {
  Memory mem=currentProgram.getMemory();
  MemoryBlock raw=mem.getBlock("ROM_FILE_REFERENCE");
  MemoryBlock norm=mem.getBlock("ROM_NORMAL_0000_7FFF");
  if(raw==null || norm==null || raw.getSize()!=65536) throw new IllegalStateException("Wrong project");
  byte[] rom=new byte[65536]; mem.getBytes(raw.getStart(),rom);
  String hash=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(rom));
  if(!hash.equals("7c8d2aecbb74bf939661d3fd904c691a4c7c749a374cb804c0247b64b649e1c2")) throw new IllegalStateException(hash);
  StringBuilder out=new StringBuilder("C ROM SHA256 "+hash+"\nCPU addresses; static disassembly; branch and bank selection unresolved.\n");
  int[][] spans={{0x0368,0x0395},{0x07a8,0x07e3},{0x04ca,0x051b},{0x0d7b,0x0d9a},{0x0f25,0x0f35},{0x1df0,0x1f20},{0x418a,0x418f},{0x4191,0x4199},{0x419a,0x41a0},{0x41a1,0x41c8},{0x4b25,0x4ba3},{0x4c86,0x4c9d},{0x4d19,0x4d55},{0x50e8,0x5149},{0x5b13,0x5bb1},{0x5d28,0x5d63},{0x5e06,0x5ea9},{0x5f3c,0x5fff},{0x6ed1,0x6f03},{0x7654,0x76d0},{0x772f,0x7763},{0x7764,0x7777}};
  AddressSet region=new AddressSet(norm.getStart(),norm.getEnd());
  for(int[] span:spans){
   Address a=toAddr(span[0]);
   DisassembleCommand d=new DisassembleCommand(a,region,true); d.enableCodeAnalysis(false); d.applyTo(currentProgram,monitor);
   out.append(String.format("\n[%04X-%04X]\n",span[0],span[1]));
   AddressSet range=new AddressSet(a,toAddr(span[1]));
   for(InstructionIterator it=currentProgram.getListing().getInstructions(range,true);it.hasNext();){
    Instruction ins=it.next();out.append(ins.getAddress()).append(' ').append(ins).append('\n');
   }
  }
  Files.writeString(Path.of(getScriptArgs()[0]),out);
  println("Tempo/rhythm evidence exported: "+getScriptArgs()[0]);
 }
}
