// Hash-checked command-state dispatch and serializer reachability evidence.
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

public class D20TraceSongCommands extends GhidraScript {
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
        byte[] mapped = new byte[32768];
        memory.getBytes(normal.getStart(), mapped);
        if (!java.util.Arrays.equals(mapped, java.util.Arrays.copyOf(rom,32768)))
            throw new IllegalStateException("Normal view differs from checked reference ROM");
        StringBuilder out = new StringBuilder("C 1.11 SHA256 " + hash
            + "\nNormal C8/18/18. Static branches are not proof of active runtime mode.\n");
        int[][] spans = {{0x01f3,0x01fb},{0x0c17,0x0cb8},{0x0d20,0x11da},{0x11db,0x172d},{0x186e,0x189a},
            {0x0250,0x0290},{0x0800,0x0850},{0x1adf,0x1af0},{0x1c10,0x1c22},
            {0x1f50,0x210d},{0x2560,0x2620},{0x2780,0x2820},{0x2a40,0x2ab0},
            {0x3460,0x34b8},{0x3524,0x3564},{0x3de0,0x3e15},{0x3ff6,0x401d},{0x418a,0x41e0},{0x4561,0x45b1},{0x4230,0x4250},{0x6fdc,0x70eb},
            {0x74f0,0x75e8},{0x79e8,0x7b54},{0x7ec0,0x7fff},{0x7b55,0x7ea0}};
        int[][] tables = {{0x0db9,8},{0x0dc7,13},{0x1232,8},{0x1240,16},{0x1260,39}};
        AddressSet region = new AddressSet(normal.getStart(), normal.getEnd());
        java.util.Set<Integer> seeds = new java.util.TreeSet<>();
        for (int seed : new int[]{0x0d20,0x11db,0x186e,0x70b1,0x70cf,0x74f0,
                0x01f3,0x080e,0x0817,0x1c10,0x1f50,0x1f6c,0x1f99,0x1fc1,
                0x1ff9,0x2006,0x2010,0x3de6,0x3ea6,0x4230,0x256f,0x257e,
                0x2593,0x2618,0x2a54,0x2aa6,0x3469,0x0c17,0x027c,0x0846,0x1adf,0x1c17,0x20d2,0x209a,0x2063,0x2040,
                0x3df0,0x423d,0x4561,0x418a,0x3524,0x3493,0x4001,
                0x7537,0x758f,0x6801,0x68dd,0x6d55,0x7ec0,0x79e8,0x7a3d,0x7a5c,0x7a8f,0x7abd}) seeds.add(seed);
        for (int[] table : tables) {
            out.append(String.format("\nDispatch %04X, %d entries:\n",table[0],table[1]));
            for (int i=0;i<table[1];i++) {
                int at=table[0]+2*i;
                int target=(rom[at]&255)|((rom[at+1]&255)<<8);
                out.append(String.format("%02X -> %04X\n",i,target));
                seeds.add(target);
            }
        }
        for (int seed : seeds) {
            if (seed<0 || seed>=32768) throw new IllegalStateException("Dispatch outside normal ROM");
            DisassembleCommand command = new DisassembleCommand(normal.getStart().add(seed), region, true);
            command.enableCodeAnalysis(false);
            command.applyTo(currentProgram, monitor);
        }
        for (int[] span : spans) {
            Address first = normal.getStart().add(span[0]);
            out.append(String.format("\n[%04X-%04X]\n",span[0],span[1]));
            for (InstructionIterator it = currentProgram.getListing().getInstructions(
                    new AddressSet(first, normal.getStart().add(span[1])), true); it.hasNext();) {
                Instruction ins = it.next();
                out.append(ins.getAddress()).append(' ').append(HexFormat.of().formatHex(ins.getBytes()))
                    .append(' ').append(ins).append('\n');
            }
        }
        out.append("\nDecoded direct serializer / recording-helper calls in normal view:\n");
        for (InstructionIterator it=currentProgram.getListing().getInstructions(region,true);it.hasNext();) {
            Instruction ins=it.next();
            for (Address target:ins.getFlows()) {
                if (target.getOffset()==0x6fdc || target.getOffset()==0x68dd)
                    out.append(ins.getAddress()).append(' ').append(ins).append('\n');
            }
        }
        for (int target : new int[]{0x6fdc,0x68dd}) {
            int rawCount=0, decodedCount=0;
            for (int i=1;i<0x7fff;i++) {
                if ((rom[i]&255)!=(target&255) || (rom[i+1]&255)!=(target>>8)) continue;
                rawCount++;
                Instruction ins=currentProgram.getListing().getInstructionAt(normal.getStart().add(i-1));
                boolean matched=false;
                if (ins!=null) for (Address flow:ins.getFlows())
                    if (flow.getOffset()==target) matched=true;
                if (matched) decodedCount++;
                else out.append(String.format("UNRESOLVED operand %04X for %04X\n",i,target));
            }
            out.append(String.format("RECONCILE %04X: raw=%d decoded=%d\n",target,rawCount,decodedCount));
        }
        out.append("\nRaw direct operands / possible code or data; normal half only:\n");
        for (int target : new int[]{0x6fdc,0x68dd,0xb416,0xb418,0xb41c,0xb426,0xb428,0x9a00,0x8828,0x88b8}) {
            out.append(String.format("target %04X:",target));
            for (int i=0;i<0x7fff;i++)
                if ((rom[i]&255)==(target&255) && (rom[i+1]&255)==(target>>8))
                    out.append(String.format(" %04X",i));
            out.append('\n');
        }
        Files.writeString(Path.of(getScriptArgs()[0]),out);
        println("Exported command-state evidence to " + getScriptArgs()[0]);
    }
}
