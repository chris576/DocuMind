import { Injectable, NotFoundException, ForbiddenException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { createHash, randomBytes } from 'crypto';
import { ExternalToken } from './entities/external-token.entity';
import { ExternalTokenUsage } from './entities/external-token-usage.entity';
import { CreateTokenDto, TokenResponseDto } from '@paperless/shared';

@Injectable()
export class ExternalApiService {
  constructor(
    @InjectRepository(ExternalToken)
    private tokenRepository: Repository<ExternalToken>,
    @InjectRepository(ExternalTokenUsage)
    private usageRepository: Repository<ExternalTokenUsage>,
  ) {}

  private generateToken(): string {
    return `pa_${randomBytes(32).toString('hex')}`;
  }

  private hashToken(token: string): string {
    return createHash('sha256').update(token).digest('hex');
  }

  private getTokenPrefix(token: string): string {
    return token.substring(0, 12);
  }

  async createToken(userId: number, dto: CreateTokenDto): Promise<TokenResponseDto> {
    const token = this.generateToken();
    const tokenHash = this.hashToken(token);
    const tokenPrefix = this.getTokenPrefix(token);

    const externalToken = this.tokenRepository.create({
      userId,
      name: dto.name,
      tokenHash,
      tokenPrefix,
      scopes: dto.scopes,
      monthlyLimit: dto.monthlyLimit,
      expiresAt: dto.expiresAt ? new Date(dto.expiresAt) : null,
    });

    const saved = await this.tokenRepository.save(externalToken);

    return {
      id: saved.id,
      token,
      name: saved.name,
      prefix: saved.tokenPrefix,
      scopes: saved.scopes,
      monthlyLimit: saved.monthlyLimit,
      expiresAt: saved.expiresAt?.toISOString(),
    };
  }

  async findAllByUser(userId: number): Promise<Partial<ExternalToken>[]> {
    const tokens = await this.tokenRepository.find({
      where: { userId },
      order: { createdAt: 'DESC' },
    });

    return tokens.map((t) => ({
      id: t.id,
      name: t.name,
      tokenPrefix: t.tokenPrefix,
      scopes: t.scopes,
      isActive: t.isActive,
      monthlyLimit: t.monthlyLimit,
      expiresAt: t.expiresAt,
      createdAt: t.createdAt,
      lastUsedAt: t.lastUsedAt,
    }));
  }

  async findOne(id: number, userId: number): Promise<Partial<ExternalToken>> {
    const token = await this.tokenRepository.findOne({ where: { id, userId } });
    if (!token) {
      throw new NotFoundException('Token not found');
    }
    return {
      id: token.id,
      name: token.name,
      tokenPrefix: token.tokenPrefix,
      scopes: token.scopes,
      isActive: token.isActive,
      monthlyLimit: token.monthlyLimit,
      expiresAt: token.expiresAt,
      createdAt: token.createdAt,
      lastUsedAt: token.lastUsedAt,
    };
  }

  async remove(id: number, userId: number): Promise<void> {
    const token = await this.tokenRepository.findOne({ where: { id, userId } });
    if (!token) {
      throw new NotFoundException('Token not found');
    }
    await this.tokenRepository.remove(token);
  }

  async revoke(id: number, userId: number): Promise<void> {
    const token = await this.tokenRepository.findOne({ where: { id, userId } });
    if (!token) {
      throw new NotFoundException('Token not found');
    }
    token.isActive = false;
    await this.tokenRepository.save(token);
  }

  async rotate(id: number, userId: number): Promise<TokenResponseDto> {
    const token = await this.tokenRepository.findOne({ where: { id, userId } });
    if (!token) {
      throw new NotFoundException('Token not found');
    }

    await this.revoke(id, userId);

    return this.createToken(userId, {
      name: token.name,
      scopes: token.scopes,
      monthlyLimit: token.monthlyLimit,
      expiresAt: token.expiresAt?.toISOString(),
    });
  }

  async getUsage(id: number, userId: number) {
    const token = await this.tokenRepository.findOne({ where: { id, userId } });
    if (!token) {
      throw new NotFoundException('Token not found');
    }

    const now = new Date();
    const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);

    const usage = await this.usageRepository
      .createQueryBuilder('usage')
      .select('COUNT(*)', 'requestCount')
      .addSelect('COALESCE(SUM(usage.promptTokens), 0)', 'promptTokens')
      .addSelect('COALESCE(SUM(usage.completionTokens), 0)', 'completionTokens')
      .addSelect('COALESCE(SUM(usage.totalTokens), 0)', 'totalTokens')
      .where('usage.tokenId = :id', { id })
      .andWhere('usage.timestamp >= :startOfMonth', { startOfMonth })
      .getRawOne();

    return {
      tokenId: id,
      monthlyLimit: token.monthlyLimit,
      monthlyUsage: {
        requestCount: parseInt(usage.requestCount, 10),
        promptTokens: parseInt(usage.promptTokens, 10),
        completionTokens: parseInt(usage.completionTokens, 10),
        totalTokens: parseInt(usage.totalTokens, 10),
      },
    };
  }

  async validateToken(token: string): Promise<ExternalToken | null> {
    if (!token || !token.startsWith('pa_')) {
      return null;
    }

    const tokenHash = this.hashToken(token);
    const tokenRecord = await this.tokenRepository.findOne({
      where: { tokenHash },
    });

    if (!tokenRecord || !tokenRecord.isActive) {
      return null;
    }

    if (tokenRecord.expiresAt && new Date(tokenRecord.expiresAt) < new Date()) {
      return null;
    }

    if (tokenRecord.monthlyLimit) {
      const now = new Date();
      const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
      const count = await this.usageRepository
        .createQueryBuilder('usage')
        .where('usage.tokenId = :id', { id: tokenRecord.id })
        .andWhere('usage.timestamp >= :startOfMonth', { startOfMonth })
        .getCount();

      if (count >= tokenRecord.monthlyLimit) {
        return null;
      }
    }

    tokenRecord.lastUsedAt = new Date();
    await this.tokenRepository.save(tokenRecord);

    return tokenRecord;
  }

  async trackUsage(
    tokenId: number,
    endpoint: string,
    method: string,
    latencyMs: number,
    sourceIp?: string,
    userAgent?: string,
    promptTokens = 0,
    completionTokens = 0,
    totalTokens = 0,
  ) {
    const usage = this.usageRepository.create({
      tokenId,
      endpoint,
      method,
      latencyMs,
      sourceIp,
      userAgent,
      promptTokens,
      completionTokens,
      totalTokens,
    });

    await this.usageRepository.save(usage);
  }
}
