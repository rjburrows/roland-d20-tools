// Investigate candidate upper-ROM views. Use a separate research copy.
// Mapping file offsets to physical ROM addresses is a hypothesis, not yet board-verified.
// @category RolandD20
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.mem.*;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import java.io.ByteArrayInputStream;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;

public class D20ProbeAlternateBanks extends GhidraScript {
 public void run() throws Exception {
  Memory m=currentProgram.getMemory();
  MemoryBlock raw=m.getBlock("ROM_FILE_REFERENCE");
  if(raw==null || raw.getSize()!=65536) throw new IllegalStateException("Run on the mapped research copy.");
  StringBuilder report=new StringBuilder("ALTERNATE BANK PROBE — provisional mappings\nNo board schematic verification yet. Static overlays do not track MMU changes automatically.\n");
  for(int[] view:new int[][]{{0x2000,0xa000,0x6000},{0x5000,0xd000,0x3000}}){
   int logical=view[0],file=view[1],length=view[2];
   String name=logical==0x2000?"CANDIDATE_82_18_08":"CANDIDATE_85_18_08";
   if(m.getBlock(name)!=null)throw new IllegalStateException("Probe already run; use a fresh test copy.");
   byte[] b=new byte[length];m.getBytes(raw.getStart().add(file),b);
   MemoryBlock block=m.createInitializedBlock(name,toAddr(logical),new ByteArrayInputStream(b),length,monitor,true);
   block.setRead(true);block.setWrite(false);block.setExecute(true);
   block.setComment("HYPOTHESIS: physical ROM address equals file offset. Static view only; MMU writes require manual flow interpretation.");
   AddressSet range=new AddressSet(block.getStart(),block.getEnd());
   // Diagnostic entry at 2000; second window has eight JP stubs spaced four bytes apart.
   int entries=logical==0x2000?1:8;
   for(int k=0;k<entries;k++){
    DisassembleCommand d=new DisassembleCommand(block.getStart().add(4*k),range,true);
    d.enableCodeAnalysis(false);d.applyTo(currentProgram,monitor);
   }
   report.append(String.format("\n%s logical %04X-%04X from ROM file %04X-%04X\n",name,logical,logical+length-1,file,file+length-1));
   InstructionIterator it=currentProgram.getListing().getInstructions(range,true);
   int count=0,bytes=0;
   while(it.hasNext()) {Instruction i=it.next();count++;bytes+=i.getLength();report.append(i.getAddress()).append(" ").append(i).append('\n');}
   report.append("Decoded candidate instructions: ").append(count).append("; bytes: ").append(bytes).append('\n');
   report.append("\nASCII candidates with logical addresses\n");
   for(int p=0;p<b.length;){int start=p;while(p<b.length&&(b[p]&255)>=32&&(b[p]&255)<=126)p++;
    if(p-start>=8)report.append(String.format("%04X ",logical+start)).append(new String(b,start,p-start,StandardCharsets.US_ASCII)).append('\n');
    if(p==start)p++;
   }
  }
  Path out=Path.of(getScriptArgs()[0]);Files.writeString(out,report,StandardCharsets.UTF_8);println("Probe exported: "+out);
 }
}
