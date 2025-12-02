"""Sample test data generator for NICO-Forge testing."""

from pathlib import Path


def create_test_txt():
    """Create a sample TXT file."""
    test_dir = Path("test_data")
    test_dir.mkdir(exist_ok=True)
    
    sample_text = """
Machine Learning in Modern Healthcare

Machine learning has revolutionized the healthcare industry. Doctors now use AI-powered tools to diagnose diseases more accurately and quickly than ever before. These systems analyze medical images, patient records, and genetic data to provide insights that were previously impossible to obtain.

Deep learning algorithms can detect patterns in X-rays and MRI scans that human eyes might miss. This technology has proven especially valuable in early cancer detection. Studies show that AI can identify tumors with accuracy rates exceeding 95 percent in many cases.

Natural language processing helps physicians extract meaningful information from electronic health records. This saves time and reduces administrative burden. Healthcare providers can focus more on patient care rather than paperwork.

Predictive analytics uses historical patient data to forecast health risks. Hospitals employ these models to identify patients who might develop complications after surgery. Early intervention based on these predictions can save lives and reduce healthcare costs significantly.

However, challenges remain in implementing machine learning in healthcare. Data privacy concerns must be addressed carefully. Medical professionals need training to use these tools effectively. Regulatory frameworks are still evolving to keep pace with rapid technological advancement.

Despite these obstacles, the future of healthcare looks promising. Personalized medicine powered by machine learning will become increasingly common. Patients will benefit from treatments tailored specifically to their genetic makeup and medical history.
""".strip()
    
    with open(test_dir / "sample_healthcare_en.txt", 'w', encoding='utf-8') as f:
        f.write(sample_text)
    
    print(f"✓ Created test file: {test_dir / 'sample_healthcare_en.txt'}")


if __name__ == "__main__":
    create_test_txt()
    print("\nTest data created. You can now run:")
    print("  python main.py test_data/sample_healthcare_en.txt")
