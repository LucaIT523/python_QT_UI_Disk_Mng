# 



<div align="center">
   <h1>python_QT_UI_Disk_Mng</h1>
</div>



This code implements a comprehensive digital forensics application with disk image management capabilities

### 1. Core Architecture

**Main Components**

- **Authentication System**: SQLite-based user management with SHA-256 password hashing
- **Disk Operations Engine**: Low-level device management through CLI tools
- Forensic Workflow Modules:
  - Image Acquisition (EWF format)
  - Image Conversion (VDI/VMDK)
  - Evidence Analysis
- **Virtualization Integration**: VirtualBox management for forensic analysis
- **Audit System**: Comprehensive activity logging

### 2. Key Technical Components

**A. Disk Management Core (`DiskManager` class)**

```
def mount_image(self, image, mountpoint):
    subprocess.check_call(['sudo', 'ewfmount', image, mountpoint])
```

Implements critical operations:

- Device enumeration via `lsblk`
- Mount management (EWF/Xmount)
- Loop device handling
- VirtualBox media management

**B. Forensic Workflows**

1. **Acquisition Module**:

   ```
   command = ["sudo", "ewfacquire", "-uC", case_number...]
   ```

   - Uses `ewfacquire` for disk imaging
   - Implements progress tracking
   - Maintains forensic integrity with case metadata

2. **Conversion System**:

   ```
   def xmount_image(self, image_path, cache_path, mountpoint):
       command = ['sudo', 'xmount', '--in', 'ewf'...]
   ```

   - Supports multiple output formats (VDI/VMDK)
   - Implements cache management
   - Integrates with VirtualBox CLI

**C. Security Implementation**

```
def getHashString(self, str):
    return SHA256.new(str.encode('utf-8')).hexdigest()
```

- SHA-256 password hashing
- Role-based access control (Admin/User)
- Sudo privilege escalation for low-level operations

### 3. UI System Architecture

| **Component**      | **Technology** | **Key Features**                  |
| ------------------ | -------------- | --------------------------------- |
| Main Window        | QStackedWidget | Role-based view switching         |
| Device Selector    | QComboBox      | Dynamic device enumeration        |
| Progress Tracking  | QListWidget    | Real-time operation logging       |
| Data Visualization | QTableWidget   | Tabular evidence presentation     |
| Form Validation    | QDialog        | Input sanitization & verification |

### 4. Key Features

**A. Forensic Integrity**

- Case metadata tracking (examiner info, timestamps)
- MD5 hash verification
- Immutable audit logs
- Evidence chain of custody management

**B. Performance Optimization**

- Asynchronous worker threads (`ProcessWorker`)
- Batch device enumeration
- Cached mount point management
- Progressive UI updates

**C. Cross-Platform Support**

- POSIX-compliant path handling
- Filesystem-agnostic operations
- Hardware abstraction through `lsblk`

### 5. Usage Scenarios

1. Evidence Collection
   - Disk imaging from physical drives
   - Metadata-enriched EWF creation
2. Forensic Analysis
   - Secure mounting of evidence files
   - Virtual machine integration for safe examination
3. Case Management
   - Multi-user collaboration
   - Audit trail generation
4. Format Conversion
   - EWF to VirtualBox disk conversion
   - Cross-platform evidence preparation

### 


### **Contact Us**

For any inquiries or questions, please contact us.

telegram : @topdev1012

email :  skymorning523@gmail.com

Teams :  https://teams.live.com/l/invite/FEA2FDDFSy11sfuegI