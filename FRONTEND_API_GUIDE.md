# 🏥 Good Hands API 가이드 (프론트엔드 개발자용)

## 📋 목차
1. [개발 환경 설정](#개발-환경-설정)
2. [인증 시스템](#인증-시스템)
3. [API 엔드포인트](#api-엔드포인트)
4. [데이터 구조](#데이터-구조)
5. [에러 처리](#에러-처리)
6. [파일 업로드](#파일-업로드)
7. [실제 사용 예제](#실제-사용-예제)

---

## 개발 환경 설정

### 🔗 Base URL
```
개발: http://localhost:8000
운영: [운영 서버 URL]
```

### 📚 API 문서
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 🧪 테스트 계정
```
케어기버: CG001 / password123
가디언:   GD001 / password123
관리자:   AD001 / admin123
```

---

## 인증 시스템

### 🔐 JWT 기반 인증
모든 API 요청에는 JWT 토큰이 필요합니다 (로그인 제외).

#### 로그인
```javascript
POST /api/auth/login
Content-Type: application/json

{
  "user_code": "CG001",
  "password": "password123"
}
```

#### 응답
```javascript
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user_type": "caregiver",
  "user_info": {
    "id": 1,
    "user_code": "CG001",
    "user_type": "caregiver",
    "email": "caregiver@example.com",
    "name": "김간병",
    "phone": "010-1234-5678"
  }
}
```

#### 인증 헤더 설정
```javascript
// Axios 예제
axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;

// Fetch 예제
fetch('/api/caregiver/home', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
})
```

---

## API 엔드포인트

### 👨‍⚕️ 케어기버 API

#### 홈 화면 데이터
```javascript
GET /api/caregiver/home
Authorization: Bearer <token>

// 응답
{
  "caregiver_name": "김간병",
  "today_sessions": [
    {
      "id": 1,
      "senior_name": "박할머니",
      "start_time": "2024-01-15T09:00:00",
      "status": "in_progress"
    }
  ],
  "seniors": [
    {
      "id": 1,
      "name": "박할머니",
      "age": 85,
      "diseases": ["치매", "당뇨"]
    }
  ],
  "unread_notifications": []
}
```

#### 출근 체크인
```javascript
POST /api/caregiver/attendance/checkin
Content-Type: multipart/form-data

FormData:
- senior_id: 1
- location: "서울시 강남구 테헤란로 123"
- gps_lat: 37.5665
- gps_lng: 126.9780
- photo: [File]
```

#### 퇴근 체크아웃
```javascript
POST /api/caregiver/attendance/checkout
Content-Type: multipart/form-data

FormData:
- session_id: 1
- location: "서울시 강남구 테헤란로 123"
- gps_lat: 37.5665
- gps_lng: 126.9780
- photo: [File]
```

#### 체크리스트 제출
```javascript
POST /api/caregiver/checklist
Content-Type: application/json

{
  "senior_id": 1,
  "responses": [
    {
      "question_key": "blood_pressure_check",
      "question_text": "혈압 측정을 완료했나요?",
      "answer": {
        "value": true,
        "systolic": 120,
        "diastolic": 80
      },
      "notes": "정상 범위 내"
    },
    {
      "question_key": "medication_taken",
      "question_text": "약 복용을 도왔나요?",
      "answer": {
        "value": true,
        "medications": ["혈압약", "당뇨약"]
      },
      "notes": "모든 약 정시 복용"
    }
  ]
}
```

#### 돌봄노트 제출
```javascript
POST /api/caregiver/care-note
Content-Type: application/json

{
  "senior_id": 1,
  "notes": [
    {
      "question_type": "special_moments",
      "question_text": "오늘 특별한 순간이나 기억에 남는 일이 있었나요?",
      "content": "오늘 손녀 사진을 보시며 많이 웃으셨습니다."
    },
    {
      "question_type": "family_longing",
      "question_text": "가족에 대한 그리움을 표현하셨나요?",
      "content": "아들 이야기를 자주 하시며 보고 싶다고 하셨습니다."
    }
  ]
}
```

### 👨‍👩‍👧‍👦 가디언 API

#### 홈 화면 데이터
```javascript
GET /api/guardian/home
Authorization: Bearer <token>

// 응답
{
  "guardian_name": "박아들",
  "seniors": [
    {
      "id": 1,
      "name": "박할머니",
      "age": 85,
      "latest_report_date": "2024-01-15"
    }
  ],
  "recent_reports": [
    {
      "id": 1,
      "date": "2024-01-15",
      "keywords": ["건강함", "기분좋음"],
      "summary": "오늘 어머니께서는 컨디션이 좋으셨습니다..."
    }
  ],
  "unread_notifications": []
}
```

#### 리포트 목록 조회
```javascript
GET /api/guardian/reports?page=1&size=20&senior_id=1
Authorization: Bearer <token>

// 응답
{
  "items": [
    {
      "id": 1,
      "date": "2024-01-15",
      "senior_name": "박할머니",
      "keywords": ["건강함", "기분좋음", "가족그리움"],
      "ai_score": 4.2,
      "created_at": "2024-01-15T18:00:00"
    }
  ],
  "total": 50,
  "page": 1,
  "size": 20,
  "pages": 3
}
```

#### 리포트 상세 조회
```javascript
GET /api/guardian/report/1
Authorization: Bearer <token>

// 응답
{
  "id": 1,
  "date": "2024-01-15",
  "senior_name": "박할머니",
  "caregiver_name": "김간병",
  "keywords": ["건강함", "기분좋음", "가족그리움"],
  "content": "오늘 박할머니께서는 전반적으로 건강하고 좋은 상태를 보이셨습니다...",
  "ai_comment": "어머니께서 가족을 많이 그리워하고 계십니다. 가능하다면 화상통화를 해보세요.",
  "checklist_data": {
    "health_score": 4.5,
    "mental_score": 4.0,
    "daily_score": 4.2
  },
  "special_notes": [
    "손녀 사진을 보며 웃으심",
    "아들 이야기를 자주 하심"
  ]
}
```

#### 피드백 전송
```javascript
POST /api/guardian/feedback
Content-Type: application/json

{
  "ai_report_id": 1,
  "message": "케어기버님 감사합니다. 어머니께서 좋아하시는 음식을 더 챙겨주세요.",
  "requirements": "혈압 체크를 더 자주 해주세요."
}
```

### 🤖 AI API

#### AI 리포트 생성
```javascript
POST /api/ai/generate-report
Content-Type: application/json

{
  "session_id": 1
}

// 응답
{
  "report_id": 1,
  "status": "generated",
  "keywords": ["건강함", "기분좋음", "가족그리움"],
  "ai_score": 4.2,
  "message": "AI 리포트가 성공적으로 생성되었습니다."
}
```

#### 추이 분석 조회
```javascript
GET /api/ai/trend-analysis/1?weeks=4
Authorization: Bearer <token>

// 응답
{
  "senior_id": 1,
  "analysis_period": "4주",
  "trend": "improving",
  "score_changes": [
    {"week": 1, "score": 3.8},
    {"week": 2, "score": 4.0},
    {"week": 3, "score": 4.1},
    {"week": 4, "score": 4.2}
  ],
  "insights": [
    "전반적인 건강 상태가 개선되고 있습니다",
    "정신적 안정감이 증가했습니다"
  ],
  "recommendations": [
    "현재 케어 방식을 유지하세요",
    "가족과의 소통을 늘려보세요"
  ]
}
```

---

## 데이터 구조

### 🏥 핵심 모델

#### Senior (시니어)
```javascript
{
  "id": 1,
  "name": "박할머니",
  "age": 85,
  "gender": "female",
  "photo": "/uploads/senior_1_photo.jpg",
  "diseases": ["치매", "당뇨", "고혈압"],
  "caregiver_name": "김간병",
  "guardian_name": "박아들"
}
```

#### CareSession (돌봄 세션)
```javascript
{
  "id": 1,
  "senior_id": 1,
  "caregiver_id": 1,
  "start_time": "2024-01-15T09:00:00",
  "end_time": "2024-01-15T17:00:00",
  "status": "completed", // "in_progress", "completed", "cancelled"
  "start_location": "서울시 강남구",
  "end_location": "서울시 강남구",
  "start_photo": "/uploads/checkin_1.jpg",
  "end_photo": "/uploads/checkout_1.jpg"
}
```

#### AIReport (AI 리포트)
```javascript
{
  "id": 1,
  "care_session_id": 1,
  "keywords": ["건강함", "기분좋음", "가족그리움"],
  "content": "상세 리포트 내용...",
  "ai_comment": "AI가 제안하는 구체적 행동...",
  "ai_score": 4.2,
  "special_notes": ["특이사항 1", "특이사항 2"],
  "created_at": "2024-01-15T18:00:00"
}
```

#### Checklist Response (체크리스트 응답)
```javascript
{
  "question_key": "blood_pressure_check",
  "question_text": "혈압 측정을 완료했나요?",
  "category": "health", // "health", "mental", "physical", "social", "daily"
  "answer": {
    "value": true,
    "systolic": 120,
    "diastolic": 80,
    "additional_data": {}
  },
  "notes": "정상 범위 내",
  "score": 5 // 1-5점
}
```

---

## 에러 처리

### 🚨 표준 에러 응답
```javascript
{
  "error": "UNAUTHORIZED",
  "message": "토큰이 유효하지 않습니다",
  "status_code": 401,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 주요 에러 코드
- `400 BAD_REQUEST`: 잘못된 요청 데이터
- `401 UNAUTHORIZED`: 인증 토큰 없음/만료
- `403 FORBIDDEN`: 권한 없음
- `404 NOT_FOUND`: 리소스 없음
- `422 VALIDATION_ERROR`: 데이터 유효성 검사 실패
- `500 INTERNAL_ERROR`: 서버 내부 오류

### React Native 에러 처리 예제
```javascript
// Axios interceptor
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // 토큰 만료 - 로그인 화면으로 이동
      NavigationService.navigate('Login');
    }
    return Promise.reject(error);
  }
);
```

---

## 파일 업로드

### 📸 이미지 업로드
```javascript
// React Native 예제
const uploadImage = async (imageUri, endpoint) => {
  const formData = new FormData();
  formData.append('photo', {
    uri: imageUri,
    type: 'image/jpeg',
    name: 'photo.jpg',
  });
  
  try {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'multipart/form-data',
      },
      body: formData,
    });
    
    return await response.json();
  } catch (error) {
    console.error('Upload failed:', error);
  }
};
```

### 📁 파일 제한사항
- **최대 크기**: 10MB
- **지원 형식**: JPG, PNG, GIF, WebP
- **저장 위치**: `/uploads/` 디렉토리
- **접근 URL**: `http://localhost:8000/uploads/filename.jpg`

---

## 실제 사용 예제

### 📱 React Native 전체 플로우

#### 1. 로그인 및 토큰 저장
```javascript
import AsyncStorage from '@react-native-async-storage/async-storage';

const login = async (userCode, password) => {
  try {
    const response = await fetch(`${BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_code: userCode,
        password: password
      })
    });
    
    const data = await response.json();
    
    if (response.ok) {
      await AsyncStorage.setItem('access_token', data.access_token);
      await AsyncStorage.setItem('user_type', data.user_type);
      await AsyncStorage.setItem('user_info', JSON.stringify(data.user_info));
      return data;
    } else {
      throw new Error(data.message);
    }
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
};
```

#### 2. 케어기버 홈 화면 데이터 로딩
```javascript
const CaregiverHome = () => {
  const [homeData, setHomeData] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    loadHomeData();
  }, []);
  
  const loadHomeData = async () => {
    try {
      const token = await AsyncStorage.getItem('access_token');
      const response = await fetch(`${BASE_URL}/api/caregiver/home`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setHomeData(data);
      }
    } catch (error) {
      console.error('Failed to load home data:', error);
    } finally {
      setLoading(false);
    }
  };
  
  // UI 렌더링...
};
```

#### 3. 출근 체크인 (GPS + 사진)
```javascript
import { launchCamera } from 'react-native-image-picker';
import Geolocation from '@react-native-community/geolocation';

const checkIn = async (seniorId) => {
  try {
    // 1. GPS 위치 확인
    const position = await new Promise((resolve, reject) => {
      Geolocation.getCurrentPosition(resolve, reject);
    });
    
    const { latitude, longitude } = position.coords;
    
    // 2. 사진 촬영
    const imageResult = await new Promise((resolve, reject) => {
      launchCamera({ mediaType: 'photo', quality: 0.8 }, (response) => {
        if (response.didCancel || response.error) {
          reject(response.error);
        } else {
          resolve(response.assets[0]);
        }
      });
    });
    
    // 3. 서버 전송
    const formData = new FormData();
    formData.append('senior_id', seniorId);
    formData.append('location', '현재 위치');
    formData.append('gps_lat', latitude);
    formData.append('gps_lng', longitude);
    formData.append('photo', {
      uri: imageResult.uri,
      type: imageResult.type,
      name: imageResult.fileName || 'checkin.jpg',
    });
    
    const token = await AsyncStorage.getItem('access_token');
    const response = await fetch(`${BASE_URL}/api/caregiver/attendance/checkin`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'multipart/form-data',
      },
      body: formData,
    });
    
    if (response.ok) {
      Alert.alert('성공', '출근 체크가 완료되었습니다.');
    }
    
  } catch (error) {
    Alert.alert('오류', '출근 체크에 실패했습니다.');
    console.error('Check-in error:', error);
  }
};
```

#### 4. 체크리스트 제출
```javascript
const submitChecklist = async (seniorId, responses) => {
  try {
    const token = await AsyncStorage.getItem('access_token');
    const response = await fetch(`${BASE_URL}/api/caregiver/checklist`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        senior_id: seniorId,
        responses: responses
      })
    });
    
    if (response.ok) {
      Alert.alert('성공', '체크리스트가 제출되었습니다.');
      return true;
    }
  } catch (error) {
    Alert.alert('오류', '체크리스트 제출에 실패했습니다.');
    return false;
  }
};

// 사용 예제
const checklistData = [
  {
    question_key: "blood_pressure_check",
    question_text: "혈압을 측정했나요?",
    answer: { value: true, systolic: 120, diastolic: 80 },
    notes: "정상 범위"
  },
  {
    question_key: "mood_check",
    question_text: "기분 상태는 어떤가요?",
    answer: { value: "good", mood_scale: 4 },
    notes: "밝고 활기차심"
  }
];

await submitChecklist(1, checklistData);
```

#### 5. 가디언 리포트 조회
```javascript
const ReportList = () => {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  
  const loadReports = async (pageNum = 1) => {
    setLoading(true);
    try {
      const token = await AsyncStorage.getItem('access_token');
      const response = await fetch(
        `${BASE_URL}/api/guardian/reports?page=${pageNum}&size=20`,
        {
          headers: { 'Authorization': `Bearer ${token}` }
        }
      );
      
      if (response.ok) {
        const data = await response.json();
        if (pageNum === 1) {
          setReports(data.items);
        } else {
          setReports(prev => [...prev, ...data.items]);
        }
      }
    } catch (error) {
      console.error('Failed to load reports:', error);
    } finally {
      setLoading(false);
    }
  };
  
  // 무한 스크롤 구현
  const loadMore = () => {
    if (!loading) {
      const nextPage = page + 1;
      setPage(nextPage);
      loadReports(nextPage);
    }
  };
  
  // UI 렌더링...
};
```

---

## 🔔 실시간 알림 (예정)

### WebSocket 연결 (향후 구현)
```javascript
import io from 'socket.io-client';

const connectWebSocket = (token) => {
  const socket = io(BASE_URL, {
    auth: { token }
  });
  
  socket.on('notification', (data) => {
    // 푸시 알림 표시
    showPushNotification(data);
  });
  
  socket.on('report_generated', (data) => {
    // 새 리포트 알림
    refreshReportList();
  });
  
  return socket;
};
```

---

## 🏗️ 개발 팁

### 1. 상태 관리 추천 구조
```javascript
// Redux store 구조 예제
const store = {
  auth: {
    token: null,
    userType: null,
    userInfo: null,
    isAuthenticated: false
  },
  caregiver: {
    homeData: null,
    seniors: [],
    currentSession: null
  },
  guardian: {
    reports: [],
    seniors: [],
    notifications: []
  }
};
```

### 2. API 호출 유틸리티
```javascript
// api.js
const createApiClient = (baseURL, token) => ({
  get: (url) => fetch(`${baseURL}${url}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  }),
  
  post: (url, data) => fetch(`${baseURL}${url}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  }),
  
  upload: (url, formData) => fetch(`${baseURL}${url}`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData
  })
});
```

### 3. 에러 바운더리
```javascript
class APIErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }
  
  static getDerivedStateFromError(error) {
    return { hasError: true };
  }
  
  componentDidCatch(error, errorInfo) {
    console.log('API Error:', error, errorInfo);
    // 에러 리포팅 서비스에 전송
  }
  
  render() {
    if (this.state.hasError) {
      return <ErrorScreen onRetry={() => this.setState({ hasError: false })} />;
    }
    
    return this.props.children;
  }
}
```

---

## 📞 개발 지원

### 문의 채널
- **GitHub Issues**: https://github.com/jhon829/sinabro/issues
- **개발자 이메일**: [개발자 이메일]
- **Slack 채널**: #goodhands-dev

### 추가 리소스
- **Postman Collection**: [링크 제공 예정]
- **TypeScript 타입 정의**: [링크 제공 예정]
- **예제 프로젝트**: [링크 제공 예정]

---

*이 문서는 Good Hands 프로젝트의 실제 구현을 기반으로 작성되었으며, 지속적으로 업데이트됩니다.*