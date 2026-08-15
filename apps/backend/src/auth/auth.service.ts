import { Injectable, UnauthorizedException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import * as bcrypt from 'bcryptjs';

@Injectable()
export class AuthService {
  constructor(private jwtService: JwtService) {}

  async validateUser(username: string, password: string): Promise<any> {
    // TODO: Implement actual user validation against database
    // For now, return a mock user
    if (username && password) {
      return { id: 1, username, scopes: ['user'] };
    }
    return null;
  }

  async login(user: any) {
    const payload = { username: user.username, sub: user.id, scopes: user.scopes };
    return {
      access_token: this.jwtService.sign(payload),
      user: {
        id: user.id,
        username: user.username,
        scopes: user.scopes,
      },
    };
  }

  async validateToken(token: string) {
    try {
      return this.jwtService.verify(token);
    } catch {
      throw new UnauthorizedException('Invalid token');
    }
  }
}
