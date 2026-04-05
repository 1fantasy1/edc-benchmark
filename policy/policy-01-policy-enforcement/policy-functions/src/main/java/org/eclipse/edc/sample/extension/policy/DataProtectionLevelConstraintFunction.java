/*
 *  Copyright (c) 2024 Fraunhofer-Gesellschaft zur Förderung der angewandten Forschung e.V.
 *
 *  This program and the accompanying materials are made available under the
 *  terms of the Apache License, Version 2.0 which is available at
 *  https://www.apache.org/licenses/LICENSE-2.0
 *
 *  SPDX-License-Identifier: Apache-2.0
 *
 *  Contributors:
 *       Fraunhofer-Gesellschaft zur Förderung der angewandten Forschung e.V. - initial API and implementation
 *
 */

package org.eclipse.edc.sample.extension.policy;

import org.eclipse.edc.connector.controlplane.contract.spi.policy.ContractNegotiationPolicyContext;
import org.eclipse.edc.policy.engine.spi.AtomicConstraintRuleFunction;
import org.eclipse.edc.policy.model.Operator;
import org.eclipse.edc.policy.model.Permission;
import org.eclipse.edc.spi.monitor.Monitor;

import java.util.Collection;
import java.util.HashMap;
import java.util.Map;
import java.util.regex.Pattern;

import static java.lang.String.format;

/**
 * 高复杂度约束函数：数据保护级别约束
 * 用于验证消费者的数据保护合规级别，支持多层级验证和组合条件
 * 
 * 支持的保护级别（从低到高）：
 * 0 = NONE: 无保护
 * 1 = BASIC: 基础保护（加密传输）
 * 2 = STANDARD: 标准保护（加密存储 + 传输）
 * 3 = ENHANCED: 增强保护（加密 + 访问控制）
 * 4 = MAXIMUM: 最高保护（加密 + 访问控制 + 审计日志）
 */
public class DataProtectionLevelConstraintFunction implements AtomicConstraintRuleFunction<Permission, ContractNegotiationPolicyContext> {
    
    private final Monitor monitor;
    private static final Map<String, Integer> PROTECTION_LEVELS = new HashMap<>();
    // 提取 @value 中的值
    private static final Pattern VALUE_PATTERN = Pattern.compile("\"@value\"\\s*:\\s*\"([^\"]+)\"");
    
    static {
        PROTECTION_LEVELS.put("NONE", 0);
        PROTECTION_LEVELS.put("BASIC", 1);
        PROTECTION_LEVELS.put("STANDARD", 2);
        PROTECTION_LEVELS.put("ENHANCED", 3);
        PROTECTION_LEVELS.put("MAXIMUM", 4);
    }
    
    public DataProtectionLevelConstraintFunction(Monitor monitor) {
        this.monitor = monitor;
    }
    
    /**
     * 从 ODRL 格式的值中提取实际的字符串
     * 例如: {"@value":"MAXIMUM"} 或 MAXIMUM
     */
    private String extractValueString(Object value) {
        String stringValue = value.toString();
        
        // 如果是 ODRL 对象格式 {"@value":"..."}
        if (stringValue.contains("@value")) {
            var matcher = VALUE_PATTERN.matcher(stringValue);
            if (matcher.find()) {
                return matcher.group(1);
            }
        }
        
        // 否则直接返回字符串值
        return stringValue;
    }
    
    @Override
    public boolean evaluate(Operator operator, Object rightValue, Permission rule, ContractNegotiationPolicyContext context) {
        // Get consumer's data protection level from claims
        var consumerProtectionLevel = getConsumerProtectionLevel(context);
        
        monitor.info(format("Evaluating data protection level constraint: consumer level=%s, operator=%s, required=%s",
                consumerProtectionLevel, operator, rightValue));
        
        return switch (operator) {
            case EQ -> {
                // Consumer must have exact protection level
                int requiredLevel = parseProtectionLevel(extractValueString(rightValue));
                yield consumerProtectionLevel == requiredLevel;
            }
            case GT -> {
                // Consumer must have higher protection level than required
                // This works for "GTE" by passing a level one lower
                int requiredLevel = parseProtectionLevel(extractValueString(rightValue));
                yield consumerProtectionLevel > requiredLevel;
            }
            case LT -> {
                // Consumer protection level must be lower (for maximum threshold)
                // This works for "LTE" by passing a level one higher
                int requiredLevel = parseProtectionLevel(extractValueString(rightValue));
                yield consumerProtectionLevel < requiredLevel;
            }
            case NEQ -> {
                // Consumer must NOT have this protection level
                int requiredLevel = parseProtectionLevel(extractValueString(rightValue));
                yield consumerProtectionLevel != requiredLevel;
            }
            case IN -> {
                // Consumer protection level must be in allowed set
                if (rightValue instanceof Collection<?> allowedLevels) {
                    yield allowedLevels.stream()
                            .map(this::extractValueString)
                            .mapToInt(this::parseProtectionLevel)
                            .anyMatch(level -> level == consumerProtectionLevel);
                }
                yield false;
            }
            default -> {
                // Handle IS_ANY_OF operator (output from Operator enum)
                String operatorStr = operator.toString();
                monitor.info(format("Checking default branch: operator.toString()=%s", operatorStr));
                
                if ("IS_ANY_OF".equalsIgnoreCase(operatorStr) || "isAnyOf".equalsIgnoreCase(operatorStr)) {
                    monitor.info("Handling IS_ANY_OF/isAnyOf operator for data protection level");
                    if (rightValue instanceof Collection<?> allowedLevels) {
                        try {
                            var result = allowedLevels.stream()
                                    .map(this::extractValueString)
                                    .mapToInt(this::parseProtectionLevel)
                                    .anyMatch(level -> level == consumerProtectionLevel);
                            monitor.info(format("IS_ANY_OF protection level check: consumer level=%s, allowed levels=%s, result=%s",
                                    consumerProtectionLevel, rightValue, result));
                            yield result;
                        } catch (Exception e) {
                            monitor.warning("Failed to process IS_ANY_OF data protection level: " + rightValue + ", exception: " + e.getMessage());
                            yield false;
                        }
                    } else {
                        monitor.warning(format("rightValue is not a Collection. Type: %s", rightValue.getClass().getSimpleName()));
                    }
                } else {
                    monitor.warning(format("Operator %s not recognized", operatorStr));
                }
                yield false;
            }
        };
    }
    
    /**
     * Retrieves the consumer's data protection level from their claims
     * Default level is STANDARD (2) if not specified
     */
    private int getConsumerProtectionLevel(ContractNegotiationPolicyContext context) {
        var claims = context.participantAgent().getClaims();
        var protectionLevelClaim = claims.get("dataProtectionLevel");
        
        if (protectionLevelClaim instanceof String levelStr) {
            return parseProtectionLevel(levelStr);
        } else if (protectionLevelClaim instanceof Number num) {
            return num.intValue();
        }
        
        // Default level
        monitor.debug("No data protection level found in claims, using default level: STANDARD");
        return PROTECTION_LEVELS.get("STANDARD");
    }
    
    /**
     * Parses a protection level from string or numeric representation
     */
    private int parseProtectionLevel(Object levelValue) {
        if (levelValue instanceof Number num) {
            int level = num.intValue();
            if (level >= 0 && level <= 4) {
                return level;
            }
            monitor.warning("Invalid protection level number: " + level);
            return 0;
        }
        
        String levelStr = extractValueString(levelValue).toUpperCase();
        Integer level = PROTECTION_LEVELS.get(levelStr);
        
        if (level != null) {
            return level;
        }
        
        monitor.warning("Unknown protection level: " + levelStr);
        return 0;
    }
    
    /**
     * Helper method to get all available protection levels (for documentation)
     */
    public static Map<String, Integer> getAvailableLevels() {
        return new HashMap<>(PROTECTION_LEVELS);
    }
}
