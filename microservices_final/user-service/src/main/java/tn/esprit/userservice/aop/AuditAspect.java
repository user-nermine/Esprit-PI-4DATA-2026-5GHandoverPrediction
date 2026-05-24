package tn.esprit.userservice.aop;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.stereotype.Component;
import tn.esprit.userservice.service.AuditLogService;

@Aspect
@Component
@RequiredArgsConstructor
@Slf4j
public class AuditAspect {

    private final AuditLogService auditLogService;

    @Around("execution(* tn.esprit.userservice.controller.*.*(..))")
    public Object logExecutionTime(ProceedingJoinPoint joinPoint) throws Throwable {
        long startTime = System.currentTimeMillis();

        String methodName = joinPoint.getSignature().getName();
        String className = joinPoint.getTarget().getClass().getSimpleName();
        Object[] args = joinPoint.getArgs();

        log.debug("🔵 Method called: {}.{}", className, methodName);

        String status = "SUCCESS";
        String errorMessage = null;
        Object result = null;

        String userEmail = extractEmailFromArgs(args);

        try {
            result = joinPoint.proceed();
            return result;
        } catch (Exception e) {
            status = "FAILED";
            errorMessage = e.getMessage();
            log.error("🔴 Error in {}.{}: {}", className, methodName, e.getMessage());
            throw e;
        } finally {
            long executionTime = System.currentTimeMillis() - startTime;

            // args.length retourne un int - c'est correct
            auditLogService.saveLog(userEmail, className, methodName,
                    args.length,  // ← int
                    status, errorMessage, executionTime);

            log.debug("🟢 Method {}.{} executed in {} ms", className, methodName, executionTime);
        }
    }

    private String extractEmailFromArgs(Object[] args) {
        if (args == null) return "anonymous";
        for (Object arg : args) {
            if (arg != null) {
                try {
                    java.lang.reflect.Method method = arg.getClass().getMethod("getEmail");
                    Object email = method.invoke(arg);
                    if (email != null) return email.toString();
                } catch (Exception e) {
                    // Ignorer
                }
                try {
                    java.lang.reflect.Field field = arg.getClass().getDeclaredField("email");
                    field.setAccessible(true);
                    Object email = field.get(arg);
                    if (email != null) return email.toString();
                } catch (Exception e) {
                    // Ignorer
                }
            }
        }
        return "anonymous";
    }
}