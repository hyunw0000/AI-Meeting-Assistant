  const handleGoogleLogin = async (e: React.MouseEvent) => {
    e.preventDefault();
    console.log("로그인 버튼 클릭됨 - 강제 리다이렉트 시도");
    
    try {
      const host = window.location.hostname || '101.79.22.220';
      const res = await fetch(`http://${host}:8000/api/v1/calendar/auth`);
      const data = await res.json();
      
      console.log("백엔드 응답 데이터:", data);
      
      // auth_url을 추출합니다. (백엔드가 JSON 객체로 반환하므로)
      const targetUrl = data.auth_url;
      
      if (targetUrl) {
        console.log("이동할 주소로 강제 리다이렉트 수행:", targetUrl);
        window.location.assign(targetUrl); // location.href 대신 assign 사용
      } else {
        alert("로그인 주소를 가져오지 못했습니다.");
      }
    } catch (err) {
      console.error("로그인 프로세스 중 치명적 오류:", err);
      alert("로그인 서버와 통신할 수 없습니다.");
    }
  }