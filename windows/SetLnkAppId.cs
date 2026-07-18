using System;
using System.Runtime.InteropServices;

namespace LnkFix {
  [ComImport, Guid("000214F9-0000-0000-C000-000000000046"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  interface IShellLinkW {
    void GetPath([Out, MarshalAs(UnmanagedType.LPWStr)] System.Text.StringBuilder pszFile, int cchMaxPath, IntPtr pfd, int fFlags);
    void GetIDList(out IntPtr ppidl);
    void SetIDList(IntPtr pidl);
    void GetDescription([Out, MarshalAs(UnmanagedType.LPWStr)] System.Text.StringBuilder pszName, int cchMaxName);
    void SetDescription([MarshalAs(UnmanagedType.LPWStr)] string pszName);
    void GetWorkingDirectory([Out, MarshalAs(UnmanagedType.LPWStr)] System.Text.StringBuilder pszDir, int cchMaxPath);
    void SetWorkingDirectory([MarshalAs(UnmanagedType.LPWStr)] string pszDir);
    void GetArguments([Out, MarshalAs(UnmanagedType.LPWStr)] System.Text.StringBuilder pszArgs, int cchMaxPath);
    void SetArguments([MarshalAs(UnmanagedType.LPWStr)] string pszArgs);
    void GetHotkey(out short pwHotkey);
    void SetHotkey(short wHotkey);
    void GetShowCmd(out int piShowCmd);
    void SetShowCmd(int iShowCmd);
    void GetIconLocation([Out, MarshalAs(UnmanagedType.LPWStr)] System.Text.StringBuilder pszIconPath, int cchIconPath, out int piIcon);
    void SetIconLocation([MarshalAs(UnmanagedType.LPWStr)] string pszIconPath, int iIcon);
    void SetRelativePath([MarshalAs(UnmanagedType.LPWStr)] string pszPathRel, int dwReserved);
    void Resolve(IntPtr hwnd, int fFlags);
    void SetPath([MarshalAs(UnmanagedType.LPWStr)] string pszFile);
  }

  [ComImport, Guid("0000010b-0000-0000-C000-000000000046"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  interface IPersistFile {
    void GetClassID(out Guid pClassID);
    void IsDirty();
    void Load([MarshalAs(UnmanagedType.LPWStr)] string pszFileName, uint dwMode);
    void Save([MarshalAs(UnmanagedType.LPWStr)] string pszFileName, [MarshalAs(UnmanagedType.Bool)] bool fRemember);
    void SaveCompleted([MarshalAs(UnmanagedType.LPWStr)] string pszFileName);
    void GetCurFile([MarshalAs(UnmanagedType.LPWStr)] out string ppszFileName);
  }

  [ComImport, Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  interface IPropertyStore {
    uint GetCount(out uint cProps);
    uint GetAt(uint iProp, out PropertyKey pkey);
    uint GetValue(ref PropertyKey key, out PropVariant pv);
    uint SetValue(ref PropertyKey key, ref PropVariant pv);
    uint Commit();
  }

  [StructLayout(LayoutKind.Sequential, Pack = 4)]
  struct PropertyKey {
    public Guid fmtid;
    public uint pid;
    public PropertyKey(Guid f, uint p) { fmtid = f; pid = p; }
  }

  [StructLayout(LayoutKind.Sequential)]
  struct PropVariant {
    public ushort vt;
    public ushort wReserved1, wReserved2, wReserved3;
    public IntPtr pointerValue;
    public static PropVariant FromString(string value) {
      var pv = new PropVariant();
      pv.vt = 31;
      pv.pointerValue = Marshal.StringToCoTaskMemUni(value);
      return pv;
    }
  }

  class Program {
    static int Main(string[] args) {
      if (args.Length < 6) return 1;
      string lnkPath = args[0], target = args[1], arguments = args[2], workDir = args[3], icon = args[4], appId = args[5];
      var t = Type.GetTypeFromCLSID(new Guid("00021401-0000-0000-C000-000000000046"));
      var link = (IShellLinkW)Activator.CreateInstance(t);
      link.SetPath(target);
      link.SetArguments(arguments);
      link.SetWorkingDirectory(workDir);
      link.SetIconLocation(icon, 0);
      link.SetDescription("Read Aloud");
      var store = (IPropertyStore)link;
      var key = new PropertyKey(new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), 5);
      var pv = PropVariant.FromString(appId);
      store.SetValue(ref key, ref pv);
      store.Commit();
      var file = (IPersistFile)link;
      file.Save(lnkPath, true);
      Marshal.FreeCoTaskMem(pv.pointerValue);
      Console.WriteLine("Updated " + lnkPath);
      return 0;
    }
  }
}
