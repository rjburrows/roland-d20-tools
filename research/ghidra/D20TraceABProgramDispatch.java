// Trace fixed and explicitly qualified bank-3 program dispatch candidates.
// @category RolandD20
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import java.io.ByteArrayInputStream;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.HexFormat;

public class D20TraceABProgramDispatch extends GhidraScript {
 public void run() throws Exception {
  Memory memory=currentProgram.getMemory();
  MemoryBlock flat=memory.getBlock(currentProgram.getMinAddress());
  if(flat==null||flat.getSize()!=65536) throw new IllegalStateException("Expected flat interleaved A/B");
  byte[] rom=new byte[65536]; memory.getBytes(flat.getStart(),rom);
  String hash=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(rom));
  if(!hash.equals("283cda5527d3b21cc39093cdcb0f982f0399466585b871b9fa77ac3ae855f2ca"))
   throw new IllegalStateException("Unexpected image "+hash);
  StringBuilder out=new StringBuilder("A/B 1.12 SHA256 "+hash+"\n"
   +"Fixed-file listings provisional CPU interpretation. Bank3 candidate maps file C000-FFFF to CPU8000-BFFF; mapping must be checked against callers and gate array.\n");
  for(int[] s:new int[][]{{0x2080,0x2187},{0x2188,0x2380},{0x1f27,0x1fff},
     {0x1d94,0x1f26},{0x778d,0x78ff},{0x6132,0x61c0},{0x5a41,0x5ab0},
     {0x5a70,0x5b10},{0x873f,0x87d0},{0x83fb,0x8440},
     {0x8500,0x86c0},{0x86e6,0x873e},{0x5ace,0x5b45},
     {0x8000,0x83fa},{0x55fa,0x56a0},{0x2a97,0x2b2a},{0x1c45,0x1cb3},
     {0x3f27,0x4020},{0x5fef,0x6020},{0x5f34,0x5f58},
     {0x61b5,0x6263},{0x6319,0x63d5},{0x7e87,0x7fff},
     {0x4013,0x419b},{0x3f18,0x3f26},{0x5a11,0x5a40}})
    export(flat,0,s[0],s[1],out);
  MemoryBlock bank=memory.getBlock("AB_PROGRAM_BANK03_CANDIDATE");
  if(bank==null) bank=memory.createInitializedBlock("AB_PROGRAM_BANK03_CANDIDATE",toAddr(0x8000),
    new ByteArrayInputStream(rom,0xc000,0x4000),0x4000,monitor,true);
  bank.setRead(true);bank.setWrite(false);bank.setExecute(true);
  for(int vector=0x8000;vector<=0x802c;vector+=4) export(bank,0x8000,vector,vector+3,out);
  for(int[] s:new int[][]{{0x8036,0x80a0},{0x803a,0x8040},{0x80a0,0x8200},
      {0x82ef,0x83e0},{0x8800,0x8940},{0x9200,0x92c0}}) export(bank,0x8000,s[0],s[1],out);
  out.append("\nRaw CMPB immediate C0 candidates (not necessarily code):\n");
  for(int i=0;i<rom.length-2;i++) if((rom[i]&255)==0x99&&(rom[i+1]&255)==0xc0)
    out.append(String.format("file %04X register %02X\n",i,rom[i+2]&255));
  out.append("\nFixed dispatch table 6264 and flags 6274:\n");
  for(int i=0;i<8;i++) out.append(String.format("status %02X target %04X flag %02X\n",
      0x80+16*i,(rom[0x6264+2*i]&255)+256*(rom[0x6265+2*i]&255),rom[0x6274+i]&255));
  out.append("\nPatch scatter destinations 419C (38 words):\n");
  for(int i=0;i<38;i++) out.append(String.format("%d %04X\n",i,
      (rom[0x419c+2*i]&255)+256*(rom[0x419d+2*i]&255)));
  Files.writeString(Path.of(getScriptArgs()[0]),out);
 }
 private void export(MemoryBlock block,int base,int first,int last,StringBuilder out)throws Exception {
  Address start=block.getStart().add(first-base),end=block.getStart().add(last-base);
  DisassembleCommand cmd=new DisassembleCommand(start,new AddressSet(block.getStart(),block.getEnd()),true);
  cmd.enableCodeAnalysis(false);cmd.applyTo(currentProgram,monitor);
  out.append(String.format("\n[%s %04X-%04X]\n",block.getName(),first,last));
  for(InstructionIterator it=currentProgram.getListing().getInstructions(new AddressSet(start,end),true);it.hasNext();) {
   Instruction ins=it.next();out.append(ins.getAddress()).append(' ').append(HexFormat.of().formatHex(ins.getBytes())).append(' ').append(ins).append('\n');
  }
 }
}
