import { CanActivate, ExecutionContext, Injectable } from '@nestjs/common';

/**
 * Minimal static bearer-token guard.
 *
 * Disabled when GATEWAY_API_TOKEN is unset. Protects every route below the
 * global `/api` prefix except `/api/health` (and Swagger at `/api-docs*`,
 * which lives outside the prefix).
 */
@Injectable()
export class GatewayAuthGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const token = process.env.GATEWAY_API_TOKEN;
    if (!token) {
      return true;
    }

    const request = context.switchToHttp().getRequest();
    const path: string = request.path || '';
    if (!path.startsWith('/api/') || path === '/api/health') {
      return true;
    }

    const authorization = request.headers?.['authorization'];
    return authorization === `Bearer ${token}`;
  }
}
