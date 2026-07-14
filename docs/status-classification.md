# Status Classification

## Band 정의

score band:

  LOW:    0 이상 ~ 30 미만

  MEDIUM: 30 이상 ~ 55 미만

  HIGH:   55 이상 ~ 75 미만

  EXTREME: 75 이상

imbalance band:

  NONE:     0 이상 ~ 20 미만

  MODERATE: 20 이상 ~ 50 미만

  SEVERE:   50 이상

## 분류 순서 (위에서 아래로, 첫 매칭에서 반환)

1. CRITICAL: heat=EXTREME AND cool>=HIGH

2. CRITICAL: cool=EXTREME AND heat>=HIGH

3. CRITICAL: heat>=HIGH AND cool>=HIGH AND imbalance=SEVERE

4. WARNING:  heat=EXTREME (단독)

5. WARNING:  cool=EXTREME (단독)

6. WARNING:  heat>=HIGH AND cool>=HIGH

7. WARNING:  imbalance=SEVERE (단독)

8. ELEVATED: heat=HIGH (단독)

9. ELEVATED: cool=HIGH (단독)

10. ELEVATED: heat=MEDIUM AND cool=MEDIUM

11. ADVISORY: heat=MEDIUM AND cool=LOW AND imbalance<SEVERE

12. ADVISORY: cool=MEDIUM AND heat=LOW AND imbalance<SEVERE

13. NORMAL:  위 조건 모두 해당 없음