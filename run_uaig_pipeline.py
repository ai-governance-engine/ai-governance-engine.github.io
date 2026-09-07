import subprocess
import os
import shutil

def main():
    print("="*60)
    print(" UNIVERSAL AI GOVERNANCE (UAIG) DEPLOYMENT PIPELINE")
    print("="*60)
    
    print("\n[STEP 1] Running automated Z3 Formal Verification Tests (CSA Engine)...")
    result = subprocess.run(["python", "csa_assurance_engine.py"], capture_output=True, text=True)
    if result.returncode != 0:
        print("ERROR: CSA Engine failed.")
        print(result.stderr)
        return
    print(result.stdout)
    
    print("\n[STEP 2] Generating Regulatory Traceability Matrix & Assurance Report...")
    result2 = subprocess.run(["python", "csa_report_generator.py"], capture_output=True, text=True)
    if result2.returncode != 0:
        print("ERROR: Report Generator failed.")
        print(result2.stderr)
        return
    print(result2.stdout)
    
    # Copy report to artifacts for user to see
    artifact_dir = r'C:\Users\justi\.gemini\antigravity\brain\4137e653-55a9-41c2-972e-5a842c8978b5'
    shutil.copy("UAIG_CSA_Validation_Report.md", os.path.join(artifact_dir, "UAIG_CSA_Validation_Report.md"))
    
    print("\n" + "="*60)
    print(" DEPLOYMENT SUCCESS: The UAIG proxy is locked down and formally validated.")
    print("="*60)

if __name__ == '__main__':
    main()
