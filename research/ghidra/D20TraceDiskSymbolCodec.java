// Evidence-only trace of the C 1.11 ROM's alternate-bank disk symbol codec.
// @category RolandD20
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.HexFormat;

public class D20TraceDiskSymbolCodec extends GhidraScript {
 public void run() throws Exception {
  Memory memory = currentProgram.getMemory();
  MemoryBlock raw = memory.getBlock("ROM_FILE_REFERENCE");
  MemoryBlock bank = memory.getBlock("CANDIDATE_85_18_08");
  if (raw == null || raw.getSize() != 65536 || bank == null || bank.getSize() != 0x3000)
   throw new IllegalStateException("Expected C 1.11 research copy with candidate 85/18/08 bank");
  byte[] rom = new byte[65536];
  memory.getBytes(raw.getStart(), rom);
  String hash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(rom));
  if (!hash.equals("7c8d2aecbb74bf939661d3fd904c691a4c7c749a374cb804c0247b64b649e1c2"))
   throw new IllegalStateException("Unexpected ROM hash: " + hash);
  for (int i=0; i<32; i++)
   if (memory.getByte(bank.getStart().add(0x25ad+i)) != rom[0xf5ad+i])
    throw new IllegalStateException("Candidate bank does not agree with raw ROM");
  StringBuilder out = new StringBuilder("C 1.11 ROM SHA256 " + hash + "\n"
    + "Candidate MMU 85/18/08 mapping: logical 5000-7FFF = ROM file D000-FFFF."
    + " Physical mapping not verified on board.\n\n");
  AddressSet region = new AddressSet(bank.getStart(),bank.getEnd());
  for (int[] span : new int[][]{{0x6f1c,0x6f35},{0x6faf,0x6fdd},
    {0x70aa,0x70e2},{0x73dd,0x74e7},{0x74e9,0x75ac}}) {
   Address start = bank.getStart().add(span[0]-0x5000);
   Address end = bank.getStart().add(span[1]-0x5000);
   DisassembleCommand command = new DisassembleCommand(start,region,true);
   command.enableCodeAnalysis(false);
   command.applyTo(currentProgram,monitor);
   out.append(String.format("[%04X-%04X]\n",span[0],span[1]));
   for (InstructionIterator it=currentProgram.getListing().getInstructions(new AddressSet(start,end),true);it.hasNext();) {
    Instruction ins=it.next();out.append(ins.getAddress()).append(' ').append(ins).append('\n');
   }
   out.append('\n');
  }
  out.append("Lookup at ROM offset F5AD (logical 75AD), 32 bytes:\n");
  for (int i=0;i<32;i++) out.append(String.format("%02X%s",rom[0xf5ad+i]&255,i==31?"\n":" "));
  Files.writeString(Path.of(getScriptArgs()[0]),out);
  println("Exported " + getScriptArgs()[0]);
 }
}
