"""
JSON-LD Schema.org 结构化数据生成模块
生成符合 Schema.org 规范的 JSON-LD 代码，提升品牌在 AI 模型中的实体识别和权威性
"""
from typing import Dict, List, Optional
import json
from datetime import datetime


class SchemaGenerator:
    """Schema.org JSON-LD 生成器"""
    
    def __init__(self):
        # Schema.org 上下文
        self.context = "https://schema.org"
    
    def generate_organization_schema(
        self,
        brand_name: str,
        description: str = "",
        url: str = "",
        logo: str = "",
        founding_date: str = "",
        contact_point: Dict = None
    ) -> Dict:
        """
        生成 Organization（组织）类型的 Schema
        
        Args:
            brand_name: 品牌/组织名称
            description: 组织描述
            url: 官网 URL
            logo: Logo URL
            founding_date: 成立日期（YYYY-MM-DD）
            contact_point: 联系方式（可选）
            
        Returns:
            JSON-LD Schema 字典
        """
        schema = {
            "@context": self.context,
            "@type": "Organization",
            "name": brand_name
        }
        
        if description:
            schema["description"] = description
        
        if url:
            schema["url"] = url
        
        if logo:
            schema["logo"] = logo
        
        if founding_date:
            schema["foundingDate"] = founding_date
        
        if contact_point:
            schema["contactPoint"] = {
                "@type": "ContactPoint",
                **contact_point
            }
        
        return schema
    
    def generate_software_application_schema(
        self,
        brand_name: str,
        application_name: str = "",
        description: str = "",
        url: str = "",
        application_category: str = "BusinessApplication",
        operating_system: str = "",
        offers: Dict = None,
        aggregate_rating: Dict = None,
        feature_list: List[str] = None
    ) -> Dict:
        """
        生成 SoftwareApplication（软件应用）类型的 Schema
        
        Args:
            brand_name: 品牌名称
            application_name: 应用名称（默认使用品牌名称）
            description: 应用描述
            url: 应用 URL
            application_category: 应用类别（如 BusinessApplication, WebApplication）
            operating_system: 操作系统（如 Windows, macOS, Linux, Web）
            offers: 价格信息（可选）
            aggregate_rating: 评分信息（可选）
            feature_list: 功能列表（可选）
            
        Returns:
            JSON-LD Schema 字典
        """
        schema = {
            "@context": self.context,
            "@type": "SoftwareApplication",
            "name": application_name or brand_name,
            "applicationCategory": application_category
        }
        
        if description:
            schema["description"] = description
        
        if url:
            schema["url"] = url
        
        if operating_system:
            schema["operatingSystem"] = operating_system
        
        # 添加发布者（组织）
        schema["publisher"] = {
            "@type": "Organization",
            "name": brand_name
        }
        
        if offers:
            schema["offers"] = {
                "@type": "Offer",
                **offers
            }
        
        if aggregate_rating:
            schema["aggregateRating"] = {
                "@type": "AggregateRating",
                **aggregate_rating
            }
        
        if feature_list:
            schema["featureList"] = feature_list
        
        return schema
    
    def generate_product_schema(
        self,
        brand_name: str,
        product_name: str = "",
        description: str = "",
        url: str = "",
        product_category: str = "",
        brand: Dict = None,
        offers: Dict = None,
        aggregate_rating: Dict = None
    ) -> Dict:
        """
        生成 Product（产品）类型的 Schema
        
        Args:
            brand_name: 品牌名称
            product_name: 产品名称（默认使用品牌名称）
            description: 产品描述
            url: 产品 URL
            product_category: 产品类别
            brand: 品牌信息（可选）
            offers: 价格信息（可选）
            aggregate_rating: 评分信息（可选）
            
        Returns:
            JSON-LD Schema 字典
        """
        schema = {
            "@context": self.context,
            "@type": "Product",
            "name": product_name or brand_name
        }
        
        if description:
            schema["description"] = description
        
        if url:
            schema["url"] = url
        
        if product_category:
            schema["category"] = product_category
        
        if brand:
            schema["brand"] = {
                "@type": "Brand",
                **brand
            }
        else:
            schema["brand"] = {
                "@type": "Brand",
                "name": brand_name
            }
        
        if offers:
            schema["offers"] = {
                "@type": "Offer",
                **offers
            }
        
        if aggregate_rating:
            schema["aggregateRating"] = {
                "@type": "AggregateRating",
                **aggregate_rating
            }
        
        return schema
    
    def generate_service_schema(
        self,
        brand_name: str,
        service_name: str = "",
        description: str = "",
        url: str = "",
        service_type: str = "",
        provider: Dict = None,
        area_served: str = "",
        offers: Dict = None
    ) -> Dict:
        """
        生成 Service（服务）类型的 Schema
        
        Args:
            brand_name: 品牌名称
            service_name: 服务名称（默认使用品牌名称）
            description: 服务描述
            url: 服务 URL
            service_type: 服务类型
            provider: 服务提供者信息（可选）
            area_served: 服务区域
            offers: 价格信息（可选）
            
        Returns:
            JSON-LD Schema 字典
        """
        schema = {
            "@context": self.context,
            "@type": "Service",
            "name": service_name or brand_name
        }
        
        if description:
            schema["description"] = description
        
        if url:
            schema["url"] = url
        
        if service_type:
            schema["serviceType"] = service_type
        
        if provider:
            schema["provider"] = {
                "@type": "Organization",
                **provider
            }
        else:
            schema["provider"] = {
                "@type": "Organization",
                "name": brand_name
            }
        
        if area_served:
            schema["areaServed"] = {
                "@type": "Country",
                "name": area_served
            }
        
        if offers:
            schema["offers"] = {
                "@type": "Offer",
                **offers
            }
        
        return schema
    
    def generate_combined_schema(
        self,
        brand_name: str,
        advantages: str = "",
        schema_types: List[str] = None,
        **kwargs
    ) -> Dict:
        """
        生成组合 Schema（包含多个类型）
        
        Args:
            brand_name: 品牌名称
            advantages: 品牌优势（用于描述）
            schema_types: Schema 类型列表（如 ["Organization", "SoftwareApplication"]）
            **kwargs: 其他参数
            
        Returns:
            组合的 JSON-LD Schema 字典
        """
        if schema_types is None:
            schema_types = ["Organization", "SoftwareApplication"]
        
        schemas = []
        
        # 生成 Organization
        if "Organization" in schema_types:
            org_schema = self.generate_organization_schema(
                brand_name=brand_name,
                description=advantages or kwargs.get("description", ""),
                url=kwargs.get("url", ""),
                logo=kwargs.get("logo", ""),
                founding_date=kwargs.get("founding_date", ""),
                contact_point=kwargs.get("contact_point")
            )
            schemas.append(org_schema)
        
        # 生成 SoftwareApplication
        if "SoftwareApplication" in schema_types:
            app_schema = self.generate_software_application_schema(
                brand_name=brand_name,
                application_name=kwargs.get("application_name", brand_name),
                description=advantages or kwargs.get("description", ""),
                url=kwargs.get("url", ""),
                application_category=kwargs.get("application_category", "BusinessApplication"),
                operating_system=kwargs.get("operating_system", ""),
                offers=kwargs.get("offers"),
                aggregate_rating=kwargs.get("aggregate_rating"),
                feature_list=kwargs.get("feature_list")
            )
            schemas.append(app_schema)
        
        # 生成 Product
        if "Product" in schema_types:
            product_schema = self.generate_product_schema(
                brand_name=brand_name,
                product_name=kwargs.get("product_name", brand_name),
                description=advantages or kwargs.get("description", ""),
                url=kwargs.get("url", ""),
                product_category=kwargs.get("product_category", ""),
                brand=kwargs.get("brand"),
                offers=kwargs.get("offers"),
                aggregate_rating=kwargs.get("aggregate_rating")
            )
            schemas.append(product_schema)
        
        # 生成 Service
        if "Service" in schema_types:
            service_schema = self.generate_service_schema(
                brand_name=brand_name,
                service_name=kwargs.get("service_name", brand_name),
                description=advantages or kwargs.get("description", ""),
                url=kwargs.get("url", ""),
                service_type=kwargs.get("service_type", ""),
                provider=kwargs.get("provider"),
                area_served=kwargs.get("area_served", ""),
                offers=kwargs.get("offers")
            )
            schemas.append(service_schema)
        
        # 如果只有一个 Schema，直接返回
        if len(schemas) == 1:
            return schemas[0]
        
        # 多个 Schema 时，返回数组格式
        return schemas
    
    def format_json_ld(self, schema: Dict, indent: int = 2) -> str:
        """
        格式化 JSON-LD 为字符串（用于嵌入 HTML）
        
        Args:
            schema: Schema 字典
            indent: 缩进空格数
            
        Returns:
            格式化的 JSON 字符串
        """
        return json.dumps(schema, ensure_ascii=False, indent=indent)
    
    def generate_html_script_tag(self, schema: Dict) -> str:
        """
        生成 HTML script 标签（可直接嵌入网页）
        
        Args:
            schema: Schema 字典
            
        Returns:
            HTML script 标签字符串
        """
        json_str = self.format_json_ld(schema)
        return f'<script type="application/ld+json">\n{json_str}\n</script>'
    
    def validate_schema(self, schema: Dict) -> tuple[bool, List[str]]:
        """
        验证 Schema 的基本有效性
        
        Args:
            schema: Schema 字典
            
        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        
        # 检查必需字段
        if "@context" not in schema:
            errors.append("缺少 @context 字段")
        
        if "@type" not in schema:
            errors.append("缺少 @type 字段")
        
        if "name" not in schema:
            errors.append("缺少 name 字段")
        
        # 检查 @context 值
        if schema.get("@context") != self.context:
            errors.append(f"@context 应为 {self.context}")
        
        return len(errors) == 0, errors
    
    def get_schema_types_info(self) -> Dict[str, str]:
        """
        获取支持的 Schema 类型信息
        
        Returns:
            Schema 类型字典（类型名 -> 描述）
        """
        return {
            "Organization": "组织/公司（适合企业品牌）",
            "SoftwareApplication": "软件应用（适合 SaaS 产品、软件工具）",
            "Product": "产品（适合实体产品或数字产品）",
            "Service": "服务（适合服务类业务）"
        }
    
    def generate_for_github(self, brand_name: str, advantages: str = "", **kwargs) -> str:
        """
        为 GitHub 项目生成 JSON-LD Schema
        通常使用 SoftwareApplication 类型
        
        Args:
            brand_name: 品牌/项目名称
            advantages: 项目优势/描述
            **kwargs: 其他参数
            
        Returns:
            格式化的 JSON-LD 字符串
        """
        schema = self.generate_software_application_schema(
            brand_name=brand_name,
            application_name=kwargs.get("application_name", brand_name),
            description=advantages or kwargs.get("description", ""),
            url=kwargs.get("url", ""),
            application_category=kwargs.get("application_category", "WebApplication"),
            operating_system=kwargs.get("operating_system", "Web"),
            feature_list=kwargs.get("feature_list")
        )
        
        return self.format_json_ld(schema)
    
    def generate_for_website(self, brand_name: str, advantages: str = "", **kwargs) -> str:
        """
        为官网生成 JSON-LD Schema
        通常使用 Organization + SoftwareApplication/Product/Service 组合
        
        Args:
            brand_name: 品牌名称
            advantages: 品牌优势/描述
            **kwargs: 其他参数
            
        Returns:
            HTML script 标签字符串（可直接嵌入网页）
        """
        schema_types = kwargs.get("schema_types", ["Organization", "SoftwareApplication"])
        schema = self.generate_combined_schema(
            brand_name=brand_name,
            advantages=advantages,
            schema_types=schema_types,
            **kwargs
        )
        
        return self.generate_html_script_tag(schema)
