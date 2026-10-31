/* 등번호 유니폼과 주제 배지 — 사진·공식 로고 대신 직접 그린다.

   선수 사진은 저작권(찍은 사람)과 초상권(선수)이 있고, 대회·클럽 로고는 등록
   상표다. 공개 사이트에 허락 없이 쓰지 않는다. 그래서 유니폼은 흰 선 실루엣에
   이름·번호만 넣고, 배지는 대회·클럽을 떠올리게 하는 모양을 새로 그린다.

   번호는 클럽보다 덜 바뀌는 국가대표 번호를 쓴다. 맨유 선수만 맨유 번호. */

const KITS = [
  // [등 이름, 번호] — 뒤는 어느 팀 번호인지
  ["MESSI", 10],        // 아르헨티나
  ["RONALDO", 7],       // 포르투갈
  ["MBAPPÉ", 10],       // 프랑스
  ["VINI JR.", 7],      // 브라질
  ["RICE", 4],          // 잉글랜드
  ["KANE", 9],          // 잉글랜드
  ["YAMAL", 19],        // 스페인
  ["RODRI", 16],        // 스페인
  ["DE PAUL", 7],       // 아르헨티나
  ["B.FERNANDES", 8],   // 맨유
  ["MBEUMO", 19],       // 맨유
];

/* 유니폼 뒷면 한 장 — 흰 선 실루엣 */
function kitSVG([name, no]) {
  const shirt = "M30 10 L42 5 Q50 12 58 5 L70 10 L93 25 L82 43 L72 37 L72 106 " +
                "L28 106 L28 37 L18 43 L7 25 Z";
  // 긴 이름은 글자 폭을 줄여 등판 안에 맞춘다
  const fit = name.length > 7 ? ` textLength="40" lengthAdjust="spacingAndGlyphs"` : "";
  // width·height 를 직접 적어 둔다 — 스타일이 늦게 와도 그림이 화면을 덮지 않는다
  return `<svg class="kit" width="56" height="63" viewBox="0 0 100 112" role="img" ` +
    `aria-label="${name} ${no}">` +
    `<path d="${shirt}" fill="rgba(255,255,255,.06)" stroke="rgba(255,255,255,.85)" ` +
    `stroke-width="2.5" stroke-linejoin="round"/>` +
    `<path d="M42 5 Q50 12 58 5" fill="none" stroke="rgba(255,255,255,.85)" stroke-width="2.5"/>` +
    `<text x="50" y="33" text-anchor="middle" font-family="Pretendard Variable, Pretendard, sans-serif"` +
    ` font-size="10" font-weight="700" letter-spacing="1" fill="#fff"${fit}>${name}</text>` +
    `<text x="50" y="86" text-anchor="middle" font-family="Anton, sans-serif" font-size="44"` +
    ` fill="#fff">${no}</text>` +
    `</svg>`;
}

/* 흐르는 유니폼 줄. 끊김 없이 돌도록 같은 줄을 두 번 붙인다 */
(function renderKits() {
  const track = document.getElementById("kit-track");
  if (!track) return;
  const one = KITS.map(kitSVG).join("");
  track.innerHTML = one + one;
})();

/* 주제 배지 — 주제 id 별로. 대회·클럽을 떠올리게 하는 색과 모양을 새로 그린다.
   없는 주제는 app.js 가 이모지를 그대로 쓴다 */
const BADGES = {
  // 빨간 방패와 노란 삼지창
  "soccer-manutd":
    `<svg width="48" height="48" viewBox="0 0 48 48" aria-hidden="true"><path d="M8 6 H40 V24 Q40 38 24 44 Q8 38 8 24 Z"
      fill="#DA291C" stroke="#111" stroke-width="3"/><path d="M24 12 V36 M17 13 V21 Q17 26 24 26
      Q31 26 31 21 V13 M24 9 L21.5 14 H26.5 Z M17 10 L15 15 H19 Z M31 10 L29 15 H33 Z"
      fill="none" stroke="#FBE122" stroke-width="3" stroke-linecap="round"/></svg>`,
  // 보라 바탕에 왕관
  "soccer-epl":
    `<svg width="48" height="48" viewBox="0 0 48 48" aria-hidden="true"><circle cx="24" cy="24" r="21" fill="#3D195B"
      stroke="#111" stroke-width="3"/><path d="M12 31 L14 17 L20 24 L24 13 L28 24 L34 17 L36 31 Z"
      fill="#ffffff"/><rect x="12" y="32" width="24" height="4" fill="#00FF85"/></svg>`,
  // 빨강·노랑·빨강 띠 위에 공
  "soccer-laliga":
    `<svg width="48" height="48" viewBox="0 0 48 48" aria-hidden="true"><clipPath id="lg"><circle cx="24" cy="24" r="21"/>
      </clipPath><g clip-path="url(#lg)"><rect width="48" height="48" fill="#C60B1E"/>
      <rect y="15" width="48" height="18" fill="#FFC400"/></g><circle cx="24" cy="24" r="21"
      fill="none" stroke="#111" stroke-width="3"/><circle cx="24" cy="24" r="7" fill="#fff"
      stroke="#111" stroke-width="2"/><circle cx="24" cy="24" r="2.6" fill="#111"/></svg>`,
  // 초록 바탕에 금빛 트로피
  "soccer-worldcup":
    `<svg width="48" height="48" viewBox="0 0 48 48" aria-hidden="true"><circle cx="24" cy="24" r="21" fill="#0B6E2E"
      stroke="#111" stroke-width="3"/><path d="M16 11 H32 V18 Q32 27 24 29 Q16 27 16 18 Z
      M21 29 H27 L26 34 H22 Z M17 35 H31 V38 H17 Z" fill="#FBE122"/><path d="M16 13 Q10 13 11 18
      Q12 22 16 22 M32 13 Q38 13 37 18 Q36 22 32 22" fill="none" stroke="#FBE122" stroke-width="2"/></svg>`,
  // 태극기 — 국가 상징이라 그대로 그린다
  "soccer-korea":
    `<svg width="48" height="32" viewBox="0 0 60 40" aria-hidden="true"><rect x="1" y="1" width="58" height="38" fill="#fff"
      stroke="#111" stroke-width="2"/><g transform="translate(30 20) rotate(33.69)">
      <circle r="10" fill="#0047A0"/><path d="M-10 0 A10 10 0 0 1 10 0 A5 5 0 0 0 0 0 A5 5 0 0 1 -10 0Z"
      fill="#CD2E3A"/><g fill="#111"><rect x="-20" y="-4.5" width="1.6" height="9"/>
      <rect x="-17.4" y="-4.5" width="1.6" height="9"/><rect x="-14.8" y="-4.5" width="1.6" height="9"/>
      <rect x="13.2" y="-4.5" width="1.6" height="4"/><rect x="13.2" y="0.5" width="1.6" height="4"/>
      <rect x="15.8" y="-4.5" width="1.6" height="4"/><rect x="15.8" y="0.5" width="1.6" height="4"/>
      <rect x="18.4" y="-4.5" width="1.6" height="4"/><rect x="18.4" y="0.5" width="1.6" height="4"/></g></g>
      <g transform="translate(30 20) rotate(-33.69)" fill="#111">
      <rect x="-20" y="-4.5" width="1.6" height="9"/><rect x="-17.4" y="-4.5" width="1.6" height="4"/>
      <rect x="-17.4" y="0.5" width="1.6" height="4"/><rect x="-14.8" y="-4.5" width="1.6" height="9"/>
      <rect x="13.2" y="-4.5" width="1.6" height="4"/><rect x="13.2" y="0.5" width="1.6" height="4"/>
      <rect x="15.8" y="-4.5" width="1.6" height="9"/><rect x="18.4" y="-4.5" width="1.6" height="4"/>
      <rect x="18.4" y="0.5" width="1.6" height="4"/></g></svg>`,
  // 남색 바탕에 흰 별과 금색 고리
  "soccer-ucl":
    `<svg width="48" height="48" viewBox="0 0 48 48" aria-hidden="true"><circle cx="24" cy="24" r="21" fill="#0E1E5B"
      stroke="#111" stroke-width="3"/><circle cx="24" cy="24" r="16" fill="none" stroke="#FBE122"
      stroke-width="1.6" stroke-dasharray="2 3"/><path d="M24 11 L27.6 20.2 L37.3 20.6 L29.8 26.8
      L32.2 36.2 L24 30.8 L15.8 36.2 L18.2 26.8 L10.7 20.6 L20.4 20.2 Z" fill="#ffffff"/></svg>`,
};
