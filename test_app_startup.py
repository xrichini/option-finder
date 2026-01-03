#!/usr/bin/env python3
"""
Simple test to verify app can start and import all modules correctly
"""

import sys
import importlib

def test_app_imports():
    """Test that app.py can be imported without errors"""
    try:
        # This will execute app.py initialization
        import app
        print("✅ app.py imported successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to import app.py: {e}")
        return False

def test_module_imports():
    """Test critical module imports"""
    modules_to_test = [
        ("api.main", "API main module"),
        ("api.filtering_endpoints", "Filtering endpoints"),
        ("api.short_interest_endpoints", "Short interest endpoints"),
        ("api.hybrid_endpoints", "Hybrid endpoints"),
        ("services.advanced_filtering_service", "Advanced filtering service"),
        ("services.hybrid_screening_service", "Hybrid screening service"),
        ("services.screening_service", "Screening service"),
    ]
    
    all_passed = True
    for module_name, description in modules_to_test:
        try:
            importlib.import_module(module_name)
            print(f"✅ {description} ({module_name})")
        except Exception as e:
            print(f"❌ {description} ({module_name}): {e}")
            all_passed = False
    
    return all_passed

def test_routers():
    """Test that all routers can be instantiated"""
    try:
        from api.filtering_endpoints import filtering_router
        from api.short_interest_endpoints import short_interest_router
        from api.hybrid_endpoints import hybrid_router
        
        print("✅ filtering_router imported")
        print("✅ short_interest_router imported")
        print("✅ hybrid_router imported")
        return True
    except Exception as e:
        print(f"❌ Failed to import routers: {e}")
        return False

def test_services():
    """Test that services can be instantiated"""
    try:
        from services.advanced_filtering_service import advanced_filtering_service
        
        print("✅ advanced_filtering_service instantiated")
        
        # Verify presets exist
        presets = advanced_filtering_service.get_all_presets()
        print(f"✅ Presets available: {list(presets.keys())}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to test services: {e}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("🧪 Testing App Startup & Imports")
    print("=" * 70)
    
    results = []
    
    print("\n1️⃣ Testing Module Imports...")
    results.append(test_module_imports())
    
    print("\n2️⃣ Testing Router Imports...")
    results.append(test_routers())
    
    print("\n3️⃣ Testing Services...")
    results.append(test_services())
    
    print("\n4️⃣ Testing Full App Import...")
    results.append(test_app_imports())
    
    print("\n" + "=" * 70)
    if all(results):
        print("✅ ALL TESTS PASSED - App is ready to run!")
        print("=" * 70)
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED - Check errors above")
        print("=" * 70)
        sys.exit(1)
