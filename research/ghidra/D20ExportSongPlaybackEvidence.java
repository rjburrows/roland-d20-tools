// Reproducible, read-only instruction evidence for the stored Song event grammar.
// Run on the saved C 1.11 research copy with normal ROM 0000-7FFF mapped.
// Static disassembly does not prove every dynamic caller or timing branch.
// @category RolandD20
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.HexFormat;

public class D20ExportSongPlaybackEvidence extends GhidraScript {
 public void run() throws Exception {
  Memory m = currentProgram.getMemory();
  MemoryBlock raw = m.getBlock("ROM_FILE_REFERENCE");
  MemoryBlock normal = m.getBlock("ROM_NORMAL_0000_7FFF");
  if (raw == null || raw.getSize() != 65536 || normal == null || normal.getSize() != 32768)
   throw new IllegalStateException("Expected the saved C 1.11 banked research copy");
  byte[] rom = new byte[65536];
  m.getBytes(raw.getStart(), rom);
  String sha = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(rom));
  if (!sha.equals("7c8d2aecbb74bf939661d3fd904c691a4c7c749a374cb804c0247b64b649e1c2"))
   throw new IllegalStateException("Unexpected C ROM hash: " + sha);

  int[][] spans = {
   {0x077b,0x0793},
   {0x0d7b,0x0d9a}, {0x0f25,0x0f35},
   {0x4b7c,0x4bce}, {0x4d19,0x4d40}, {0x4f51,0x4f81},
   {0x50e8,0x5149}, {0x5529,0x5573}, {0x5726,0x5773},
   {0x5b13,0x5bb1}, {0x5e06,0x5ea9},
   {0x69ea,0x6a01}, {0x6d55,0x6d65}, {0x6eac,0x6f03}, {0x6f04,0x6fdb},
   {0x6fdc,0x70d0}, {0x70ec,0x7198}, {0x7399,0x7434},
   {0x7764,0x7803}, {0x780a,0x7836}
  };
  AddressSet region = new AddressSet(normal.getStart(), normal.getEnd());
  StringBuilder out = new StringBuilder("C 1.11 normal ROM playback evidence\nSHA256 "+sha+"\n"
   +"Addresses are CPU addresses in the normal C8/18/18 view; bank changes and"
   +" alternative branches require separate analysis.\n");
  for (int[] span: spans) {
   Address a = toAddr(span[0]);
   DisassembleCommand dis = new DisassembleCommand(a, region, true);
   dis.enableCodeAnalysis(false);
   dis.applyTo(currentProgram, monitor);
   out.append(String.format("\n[%04X-%04X]\n", span[0], span[1]));
   AddressSet window = new AddressSet(a, toAddr(span[1]));
   int count = 0;
   for (InstructionIterator it = currentProgram.getListing().getInstructions(window,true);it.hasNext();) {
    Instruction ins = it.next();
    out.append(ins.getAddress()).append(' ').append(ins).append('\n');
    count++;
   }
   if (count == 0) throw new IllegalStateException("No instructions in " + a);
  }
  out.append("\n[5EAA-5EBB duration words]\n");
  for (int i=0;i<=8;i++) {
   int lo=m.getByte(toAddr(0x5eaa+2*i))&0xff;
   int hi=m.getByte(toAddr(0x5eab+2*i))&0xff;
   out.append(String.format("selector %d: %d positions (%02X %02X)\n",i,lo+256*hi,lo,hi));
  }
  Files.writeString(Path.of(getScriptArgs()[0]), out);
  println("Playback evidence exported: "+getScriptArgs()[0]);
 }
}
