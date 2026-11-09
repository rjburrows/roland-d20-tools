// Export existing normal and candidate-bank instructions for a bounded SONG playback search.
// No RAM state or side effects are inferred from a static bank overlay.
// @category RolandD20
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import java.nio.file.*;

public class D20TraceSongPlayback extends GhidraScript {
 public void run() throws Exception {
  StringBuilder out = new StringBuilder("ROM instruction inventory (static views; untraversed branches unresolved)\n");
  for (String name : new String[]{"ROM_NORMAL_0000_7FFF", "CANDIDATE_82_18_08", "CANDIDATE_85_18_08"}) {
   MemoryBlock b = currentProgram.getMemory().getBlock(name);
   if (b == null) { out.append("MISSING ").append(name).append('\n'); continue; }
   AddressSet r = new AddressSet(b.getStart(), b.getEnd());
   if (name.equals("ROM_NORMAL_0000_7FFF")) {
    AddressSet low = new AddressSet(b.getStart(), toAddr(0x4fff));
    for (int seed : new int[]{0x0080, 0x009e, 0x038a, 0x0794, 0x079e, 0x3c85}) {
     DisassembleCommand d = new DisassembleCommand(toAddr(seed), low, true);
     d.enableCodeAnalysis(false);
     d.applyTo(currentProgram, monitor);
    }
    AddressSet upper = new AddressSet(toAddr(0x5000), toAddr(0x7fff));
    java.util.Set<Address> entries = new java.util.TreeSet<>();
    for (InstructionIterator it = currentProgram.getListing().getInstructions(low, true); it.hasNext();) {
     Instruction ins = it.next();
     for (Address target : ins.getFlows()) {
      if (upper.contains(target)) entries.add(target);
     }
    }
    out.append("NORMAL_HIGH_SEEDS ").append(entries.size()).append('\n');
    for (Address a : entries) {
     DisassembleCommand d = new DisassembleCommand(a, upper, true);
     d.enableCodeAnalysis(false);
     d.applyTo(currentProgram, monitor);
    }
    for (int seed : new int[]{0x5f3c, 0x6f04, 0x6d3a, 0x6eac, 0x70ec, 0x7399}) {
     DisassembleCommand d = new DisassembleCommand(toAddr(seed), upper, true);
     d.enableCodeAnalysis(false);
     d.applyTo(currentProgram, monitor);
    }
   }
   out.append("BLOCK ").append(name).append(' ').append(b.getStart()).append(' ').append(b.getEnd()).append('\n');
   int count = 0;
   for (InstructionIterator it = currentProgram.getListing().getInstructions(r, true); it.hasNext();) {
    Instruction ins = it.next();
    out.append(ins.getAddress()).append(' ').append(ins).append('\n');
    count++;
   }
   out.append("COUNT ").append(count).append('\n');
  }
  Files.writeString(Path.of(getScriptArgs()[0]), out);
 }
}
