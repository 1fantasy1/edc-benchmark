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

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Collection;
import java.util.regex.Pattern;

import static java.lang.String.format;

/**
 * 中等复杂度约束函数：时间范围约束
 * 用于验证请求是否在允许的时间范围内
 */
public class TimeRangeConstraintFunction implements AtomicConstraintRuleFunction<Permission, ContractNegotiationPolicyContext> {
    
    private final Monitor monitor;
    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ISO_LOCAL_DATE_TIME;
    // 提取 @value 中的时间字符串
    private static final Pattern VALUE_PATTERN = Pattern.compile("\"@value\"\\s*:\\s*\"([^\"]+)\"");
    
    public TimeRangeConstraintFunction(Monitor monitor) {
        this.monitor = monitor;
    }
    
    /**
     * 从 ODRL 格式的值中提取实际的时间字符串
     * 例如: {"@value":"2024-01-01T00:00:00"} 或 2024-01-01T00:00:00
     */
    private String extractTimeString(Object value) {
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
        var currentTime = LocalDateTime.now();
        
        monitor.info(format("Evaluating time constraint: operator=%s, rightValue=%s, currentTime=%s", 
                operator, rightValue, currentTime));
        
        return switch (operator) {
            case EQ -> {
                // Check if current time matches exact time
                try {
                    var exactTime = LocalDateTime.parse(extractTimeString(rightValue), FORMATTER);
                    yield currentTime.equals(exactTime);
                } catch (Exception e) {
                    monitor.warning("Failed to parse time: " + rightValue + ", exception: " + e.getMessage());
                    yield false;
                }
            }
            case GT -> {
                // Current time is after specified time
                try {
                    var threshold = LocalDateTime.parse(extractTimeString(rightValue), FORMATTER);
                    yield currentTime.isAfter(threshold);
                } catch (Exception e) {
                    monitor.warning("Failed to parse time: " + rightValue);
                    yield false;
                }
            }
            case LT -> {
                // Current time is before specified time
                try {
                    var threshold = LocalDateTime.parse(extractTimeString(rightValue), FORMATTER);
                    yield currentTime.isBefore(threshold);
                } catch (Exception e) {
                    monitor.warning("Failed to parse time: " + rightValue);
                    yield false;
                }
            }
            case GEQ -> {
                // Current time is after or equal to start time (lower bound)
                try {
                    var threshold = LocalDateTime.parse(extractTimeString(rightValue), FORMATTER);
                    var result = !currentTime.isBefore(threshold);
                    monitor.info(format("GEQ check: threshold=%s, currentTime=%s, result=%s", threshold, currentTime, result));
                    yield result;
                } catch (Exception e) {
                    monitor.warning("Failed to parse time for GEQ: " + rightValue + ", exception: " + e.getMessage());
                    yield false;
                }
            }
            case LEQ -> {
                // Current time is before or equal to end time (upper bound)
                try {
                    var threshold = LocalDateTime.parse(extractTimeString(rightValue), FORMATTER);
                    var result = !currentTime.isAfter(threshold);
                    monitor.info(format("LEQ check: threshold=%s, currentTime=%s, result=%s", threshold, currentTime, result));
                    yield result;
                } catch (Exception e) {
                    monitor.warning("Failed to parse time for LEQ: " + rightValue + ", exception: " + e.getMessage());
                    yield false;
                }
            }
            case IN -> {
                // Time range check: rightValue should be a collection with [startTime, endTime]
                if (rightValue instanceof Collection<?> timeRange && timeRange.size() >= 2) {
                    try {
                        var times = timeRange.stream()
                                .map(this::extractTimeString)
                                .map(t -> LocalDateTime.parse(t, FORMATTER))
                                .sorted()
                                .toList();
                        var startTime = times.get(0);
                        var endTime = times.get(1);
                        yield !currentTime.isBefore(startTime) && !currentTime.isAfter(endTime);
                    } catch (Exception e) {
                        monitor.warning("Failed to parse time range: " + rightValue + ", exception: " + e.getMessage());
                        yield false;
                    }
                }
                yield false;
            }
            default -> {
                // Handle IN (time range as array) and IS_ANY_OF operators
                String operatorStr = operator.toString();
                monitor.info(format("Checking default branch: operator.toString()=%s", operatorStr));
                
                if ("IN".equalsIgnoreCase(operatorStr) || "in".equalsIgnoreCase(operatorStr)) {
                    monitor.info("Handling IN operator for time range");
                    if (rightValue instanceof Collection<?> timeRange && timeRange.size() >= 2) {
                        try {
                            var times = timeRange.stream()
                                    .map(this::extractTimeString)
                                    .map(t -> LocalDateTime.parse(t, FORMATTER))
                                    .sorted()
                                    .toList();
                            var startTime = times.get(0);
                            var endTime = times.get(1);
                            var result = !currentTime.isBefore(startTime) && !currentTime.isAfter(endTime);
                            monitor.info(format("IN time range check: startTime=%s, endTime=%s, currentTime=%s, result=%s", 
                                    startTime, endTime, currentTime, result));
                            yield result;
                        } catch (Exception e) {
                            monitor.warning("Failed to parse time range in IN: " + rightValue + ", exception: " + e.getMessage());
                            e.printStackTrace();
                            yield false;
                        }
                    } else {
                        monitor.warning(format("rightValue is not a valid Collection or has < 2 items. Type: %s, IsCollection: %s", 
                                rightValue.getClass().getSimpleName(),
                                rightValue instanceof Collection));
                        yield false;
                    }
                } else if ("IS_ANY_OF".equalsIgnoreCase(operatorStr) || "isAnyOf".equalsIgnoreCase(operatorStr)) {
                    monitor.info("Handling IS_ANY_OF/isAnyOf operator");
                    if (rightValue instanceof Collection<?> timeRange && timeRange.size() >= 2) {
                        try {
                            var times = timeRange.stream()
                                    .map(this::extractTimeString)
                                    .map(t -> LocalDateTime.parse(t, FORMATTER))
                                    .sorted()
                                    .toList();
                            var startTime = times.get(0);
                            var endTime = times.get(1);
                            var result = !currentTime.isBefore(startTime) && !currentTime.isAfter(endTime);
                            monitor.info(format("IS_ANY_OF time range check: startTime=%s, endTime=%s, currentTime=%s, result=%s", 
                                    startTime, endTime, currentTime, result));
                            yield result;
                        } catch (Exception e) {
                            monitor.warning("Failed to parse time range in IS_ANY_OF: " + rightValue + ", exception: " + e.getMessage());
                            e.printStackTrace();
                            yield false;
                        }
                    } else {
                        monitor.warning(format("rightValue is not a valid Collection or has < 2 items. Type: %s, IsCollection: %s", 
                                rightValue.getClass().getSimpleName(),
                                rightValue instanceof Collection));
                        yield false;
                    }
                } else {
                    monitor.warning(format("Operator %s not recognized", operatorStr));
                    yield false;
                }
            }
        };
    }
}
