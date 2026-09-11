import { Body, Controller, Get, HttpException, HttpStatus, Param, Put } from '@nestjs/common';
import { AppConfigService } from './app-config.service';

@Controller('config')
export class AppConfigController {
  constructor(private configService: AppConfigService) {}

  @Get()
  getConfig() {
    return this.configService.getConfig();
  }

  @Get('slice/:name')
  getSlice(@Param('name') name: string) {
    return this.configService.getSlice(name);
  }

  @Put()
  saveConfig(@Body() body: unknown) {
    try {
      return this.configService.saveConfig(body);
    } catch (error) {
      if (error instanceof HttpException) {
        throw error;
      }
      throw new HttpException(
        `Invalid config: ${(error as Error).message}`,
        HttpStatus.BAD_REQUEST,
      );
    }
  }
}
