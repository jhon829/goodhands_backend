from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.config import settings
from app.models import *
from app.database import Base, engine
from passlib.context import CryptContext

# bcrypt 해시 컨텍스트 생성 끝
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def simple_hash(password):
    """bcrypt 해시 함수"""
    return pwd_context.hash(password)

def create_seed_data():
    """시드 데이터 생성"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("시드 데이터 생성을 시작합니다...")
        
        # 기존 데이터 삭제 (중복 방지)
        print("기존 데이터를 정리합니다...")
        db.query(SeniorDisease).delete()
        db.query(Senior).delete()
        db.query(NursingHome).delete()
        db.query(Caregiver).delete()
        db.query(Guardian).delete()
        db.query(Admin).delete()
        db.query(User).delete()
        db.commit()
        
        # 케어기버 사용자 생성
        print("케어기버 사용자를 생성합니다...")
        caregiver_user = User(
            user_code="CG001",
            user_type="caregiver",
            email="caregiver@goodhands.com",
            password_hash=simple_hash("password123"),
            is_active=True
        )
        db.add(caregiver_user)
        db.commit()
        db.refresh(caregiver_user)
        
        # 케어기버 프로필 생성
        caregiver_profile = Caregiver(
            user_id=caregiver_user.id,
            name="김간병",
            phone="010-1234-5678",
            status="active"
        )
        db.add(caregiver_profile)
        db.commit()
        db.refresh(caregiver_profile)
        
        # 가디언 사용자 생성
        print("가디언 사용자를 생성합니다...")
        guardian_user = User(
            user_code="GD001",
            user_type="guardian",
            email="guardian@goodhands.com",
            password_hash=simple_hash("password123"),
            is_active=True
        )
        db.add(guardian_user)
        db.commit()
        db.refresh(guardian_user)
        
        # 가디언 프로필 생성
        guardian_profile = Guardian(
            user_id=guardian_user.id,
            name="이가디언",
            phone="010-8765-4321",
            country="미국",
            relationship_type="자녀"
        )
        db.add(guardian_profile)
        db.commit()
        db.refresh(guardian_profile)
        
        # 관리자 사용자 생성
        print("관리자 사용자를 생성합니다...")
        admin_user = User(
            user_code="AD001",
            user_type="admin",
            email="admin@goodhands.com",
            password_hash=simple_hash("admin123"),
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        # 관리자 프로필 생성
        admin_profile = Admin(
            user_id=admin_user.id,
            name="관리자",
            permissions={"all": True}
        )
        db.add(admin_profile)
        db.commit()
        db.refresh(admin_profile)
        
        # 요양원 생성
        print("요양원 정보를 생성합니다...")
        nursing_home = NursingHome(
            name="따뜻한 요양원",
            address="서울시 강남구 논현동 123-45",
            phone="02-1234-5678",
            contact_person="박원장"
        )
        db.add(nursing_home)
        db.commit()
        db.refresh(nursing_home)
        
        # 시니어 생성
        print("시니어 정보를 생성합니다...")
        senior = Senior(
            name="박할머니",
            age=80,
            gender="여성",
            nursing_home_id=nursing_home.id,
            caregiver_id=caregiver_profile.id,
            guardian_id=guardian_profile.id
        )
        db.add(senior)
        db.commit()
        db.refresh(senior)
        
        # 시니어 질병 정보 생성
        print("시니어 질병 정보를 생성합니다...")
        senior_disease1 = SeniorDisease(
            senior_id=senior.id,
            disease_type="치매",
            severity="중등도",
            notes="알츠하이머형 치매 진단"
        )
        db.add(senior_disease1)
        
        senior_disease2 = SeniorDisease(
            senior_id=senior.id,
            disease_type="당뇨",
            severity="경증",
            notes="제2형 당뇨병"
        )
        db.add(senior_disease2)
        
        db.commit()
        
        print("시드 데이터가 성공적으로 생성되었습니다.")
        print("\n사용자 계정:")
        print("- 케어기버: CG001 / password123")
        print("- 가디언: GD001 / password123")
        print("- 관리자: AD001 / admin123")
        print(f"\n생성된 데이터:")
        print(f"- 사용자: {db.query(User).count()}명")
        print(f"- 시니어: {db.query(Senior).count()}명")
        print(f"- 요양원: {db.query(NursingHome).count()}곳")
        
    except Exception as e:
        print(f"시드 데이터 생성 중 오류 발생: {e}")
        db.rollback()
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    create_seed_data()