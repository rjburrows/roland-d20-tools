// Hash-checked recording admission and event-family evidence.
// Run on the mapped C 1.11 copy with analyzeHeadless -readOnly -noanalysis.
// @category RolandD20
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.HexFormat;

public class D20TraceSongAdmission extends GhidraScript {
    public void run() throws Exception {
        Memory memory = currentProgram.getMemory();
        MemoryBlock reference = memory.getBlock("ROM_FILE_REFERENCE");
        MemoryBlock normal = memory.getBlock("ROM_NORMAL_0000_7FFF");
        if (reference == null || normal == null || reference.getSize() != 65536)
            throw new IllegalStateException("Expected mapped C 1.11 research copy");
        byte[] rom = new byte[65536];
        memory.getBytes(reference.getStart(), rom);
        String hash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(rom));
        if (!hash.equals("7c8d2aecbb74bf939661d3fd904c691a4c7c749a374cb804c0247b64b649e1c2"))
            throw new IllegalStateException("Unexpected C ROM " + hash);
        StringBuilder out = new StringBuilder("C 1.11 SHA256 " + hash
            + "\nNormal C8/18/18. Static branches are not proof of active runtime mode.\n");
        int[][] spans = {{0x65c0,0x66e4},{0x66e5,0x6704},{0x6705,0x6731},
            {0x6732,0x6800},{0x6801,0x6833},{0x6834,0x68ad},{0x68ae,0x68dc},
            {0x68dd,0x6985},{0x69ac,0x6a16},{0x6a81,0x6b50},
            {0x7435,0x74a4},{0x6d55,0x6eab},{0x6f6a,0x70b0},{0x33f2,0x3445}};
        AddressSet region = new AddressSet(normal.getStart(), normal.getEnd());
        for (int[] span : spans) {
            Address first = normal.getStart().add(span[0]);
            DisassembleCommand command = new DisassembleCommand(first, region, true);
            command.enableCodeAnalysis(false);
            command.applyTo(currentProgram, monitor);
            out.append(String.format("\n[%04X-%04X]\n",span[0],span[1]));
            for (InstructionIterator it = currentProgram.getListing().getInstructions(
                    new AddressSet(first, normal.getStart().add(span[1])), true); it.hasNext();) {
                Instruction ins = it.next();
                out.append(ins.getAddress()).append(' ').append(HexFormat.of().formatHex(ins.getBytes()))
                    .append(' ').append(ins).append('\n');
            }
        }
        out.append("\nRaw direct operands / possible code or data; normal half only:\n");
        for (int target : new int[]{0x66e5,0x68dd,0x6705,0x6fdc,0x33f2}) {
            out.append(String.format("target %04X:",target));
            for (int i=0;i<0x7fff;i++)
                if ((rom[i]&255)==(target&255) && (rom[i+1]&255)==(target>>8))
                    out.append(String.format(" %04X",i));
            out.append('\n');
        }
        Files.writeString(Path.of(getScriptArgs()[0]),out);
        println("Exported recording admission evidence to " + getScriptArgs()[0]);
    }
}
